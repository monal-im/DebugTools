#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstring>
#include <cstdlib>
#include <regex>
#include <dirent.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <cxxabi.h>
#include <sqlite3.h>
#include <pty.h>
#include <sys/wait.h>

// Mach-O headers
#include <cstdint>

#define MH_MAGIC_64 0xfeedfacf
#define LC_SEGMENT_64 0x19
#define LC_SYMTAB 0x2
#define N_TYPE  0x0e
#define N_SECT  0x0e

struct mach_header_64 {
    uint32_t magic;
    int32_t cputype;
    int32_t cpusubtype;
    uint32_t filetype;
    uint32_t ncmds;
    uint32_t sizeofcmds;
    uint32_t flags;
    uint32_t reserved;
};

struct section_64 {
    char sectname[16];
    char segname[16];
    uint64_t addr;
    uint64_t size;
    uint32_t offset;
    uint32_t align;
    uint32_t reloff;
    uint32_t nreloc;
    uint32_t flags;
    uint32_t reserved1;
    uint32_t reserved2;
    uint32_t reserved3;
};

struct load_command {
    uint32_t cmd;
    uint32_t cmdsize;
};

struct segment_command_64 {
    uint32_t cmd;
    uint32_t cmdsize;
    char segname[16];
    uint64_t vmaddr;
    uint64_t vmsize;
    uint64_t fileoff;
    uint64_t filesize;
    int32_t maxprot;
    int32_t initprot;
    uint32_t nsects;
    uint32_t flags;
};

struct symtab_command {
    uint32_t cmd;
    uint32_t cmdsize;
    uint32_t symoff;
    uint32_t nsyms;
    uint32_t stroff;
    uint32_t strsize;
};

struct nlist_64 {
    uint32_t n_strx;
    uint8_t n_type;
    uint8_t n_sect;
    uint16_t n_desc;
    uint64_t n_value;
};

struct SymbolEntry {
    std::string name;
    uint64_t address;
};

// Recursive directory scan for symbols files, returns vector of entries
struct FileEntry {
    std::string name;
    std::string path;
    std::vector<SymbolEntry> symbols;
};

constexpr size_t MAX_SYMBOLS = 1000000;

static pid_t swift_demangler_pid = 0;
static FILE* swift_demangler_stdin = nullptr;
static FILE* swift_demangler_stdout = nullptr;

// Escape JSON strings (minimal escaping)
std::string escape_json_string(const std::string& input) {
    std::string output;
    output.reserve(input.size() * 2);
    for (char c : input) {
        switch (c) {
            case '\"': output += "\\\""; break;
            case '\\': output += "\\\\"; break;
            case '\b': output += "\\b";  break;
            case '\f': output += "\\f";  break;
            case '\n': output += "\\n";  break;
            case '\r': output += "\\r";  break;
            case '\t': output += "\\t";  break;
            default:
                if (static_cast<unsigned char>(c) < 0x20) {
                    char buf[7];
                    snprintf(buf, sizeof(buf), "\\u%04x", c);
                    output += buf;
                } else {
                    output += c;
                }
        }
    }
    return output;
}

std::string read_string(FILE* fp) {
    char buffer[65536];
    std::string result;
    if (fgets(buffer, sizeof(buffer), fp)) {
        result = buffer;
    }
    
    if (!result.empty() && result.back() == '\n') {
        result.pop_back();
    }
    if (!result.empty() && result.back() == '\r') {
        result.pop_back();
    }
    return result;
}
std::string demangle_swift_symbol(const std::string& mangled) {
    static int status = 0;
    if (status == 0) {
        waitpid(swift_demangler_pid, &status, WNOHANG);
        if (status != 0) {
            char buffer[65536];
            while (fgets(buffer, sizeof(buffer), swift_demangler_stdout)) {
                std::cerr << "swift-demangle:" << buffer;
            }
            if (swift_demangler_stdin) {
                fclose(swift_demangler_stdin);
            }
            if (swift_demangler_stdout) {
                fclose(swift_demangler_stdout);
            }
            if (WIFEXITED(status)) {
                if (WEXITSTATUS(status) != 0) {
                    std::cerr << "swift-demangle exited with code " << WEXITSTATUS(status) << std::endl;
                }
            } else {
                std::cerr << "swift-demangle terminated abnormally" << std::endl;
            }
        }
    }
    if (status != 0 || !swift_demangler_stdin || !swift_demangler_stdout) return mangled;
    
    fputs(mangled.c_str(), swift_demangler_stdin);
    fputs("\n", swift_demangler_stdin);
    fflush(swift_demangler_stdin);

    //read and ignore pty echo
    std::string echo = read_string(swift_demangler_stdout);
    if ( echo != mangled) {
        std::cerr << "Got wrong echo from swift demangler: '" << echo << "' != expected '" << mangled << "'" << std::endl;
        exit(1);
    }
    
    //read and return result
    std::string result = read_string(swift_demangler_stdout);
    return result.empty() ? mangled : result;
}

// Extract symbols from a Mach-O file
bool extract_symbols(const std::string& filepath, std::vector<SymbolEntry>& symbols) {
    symbols.clear();

    int fd = open(filepath.c_str(), O_RDONLY);
    if (fd < 0) {
        std::perror(("open " + filepath).c_str());
        return false;
    }

    struct stat st;
    if (fstat(fd, &st) != 0) {
        std::perror(("fstat " + filepath).c_str());
        close(fd);
        return false;
    }

    void* file = mmap(nullptr, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (file == MAP_FAILED) {
        std::perror(("mmap " + filepath).c_str());
        close(fd);
        return false;
    }

    mach_header_64* header = reinterpret_cast<mach_header_64*>(file);
    if (header->magic != MH_MAGIC_64) {
        // Not a valid 64-bit Mach-O file
        munmap(file, st.st_size);
        close(fd);
        return false;
    }

    load_command* cmd = reinterpret_cast<load_command*>((uint8_t*)file + sizeof(mach_header_64));
    symtab_command* symtab = nullptr;
    uint8_t text_sect_index = 0;
    uint64_t preferred_load_address = 0;

    for (uint32_t i = 0; i < header->ncmds; ++i) {
        if (cmd->cmd == LC_SEGMENT_64) {
            segment_command_64* seg = reinterpret_cast<segment_command_64*>(cmd);
            if (strncmp(seg->segname, "__TEXT", 16) == 0) {
                preferred_load_address = seg->vmaddr;
            }
            const section_64* sect = reinterpret_cast<const section_64*>(seg + 1);
            for (uint32_t j = 0; j < seg->nsects; ++j) {
                if (std::string(sect->segname) == "__TEXT") {
                    //printf("index of '%s': %d\n", sect->sectname, sect - reinterpret_cast<const section_64*>(seg + 1) + 1);
                    if(std::string(sect->sectname) == "__text") {
                        text_sect_index = sect - reinterpret_cast<const section_64*>(seg + 1) + 1;
                        break;
                    }
                }
                ++sect;
            }
        } else if (cmd->cmd == LC_SYMTAB) {
            symtab = reinterpret_cast<symtab_command*>(cmd);
        }
        cmd = reinterpret_cast<load_command*>((uint8_t*)cmd + cmd->cmdsize);
    }

    if (!symtab) {
        munmap(file, st.st_size);
        close(fd);
        return false;
    }

    nlist_64* symbols_table = reinterpret_cast<nlist_64*>((uint8_t*)file + symtab->symoff);
    const char* strtab = reinterpret_cast<const char*>((uint8_t*)file + symtab->stroff);
    for (uint32_t i = 0; i < symtab->nsyms && symbols.size() < MAX_SYMBOLS; ++i) {
        nlist_64& sym = symbols_table[i];
        // Only external symbols with a valid address
        if ((sym.n_type & N_TYPE) == N_SECT && sym.n_value != 0 && sym.n_sect == text_sect_index) {
            const char* symNameRaw = strtab + sym.n_strx;
            int status = 0;
            char* demangled = abi::__cxa_demangle(symNameRaw, nullptr, nullptr, &status);
            std::string symName = (status == 0 && demangled) ? demangled : symNameRaw;
            //don't try swift demangle, if c++ could already demangle it and only try to demangle stuff that'S marked as swift
            if ((status != 0 || !demangled) && symName.starts_with("_$s"))
            {
                std::string newSymName = demangle_swift_symbol(symName);
                if (newSymName != symName) {
                    // std::cout << "'" << symName << "' => '" << newSymName << "'" << std::endl;
                    symName = newSymName;
                }
            }
            free(demangled);
            symbols.push_back(SymbolEntry{ symName, sym.n_value - preferred_load_address });
        }
    }

    munmap(file, st.st_size);
    close(fd);
    return true;
}

// Parse dirname with regex to extract version and build
bool parse_dirname(const std::string& dirname, std::string& version, std::string& build, std::string& arch, const std::regex& re) {
    std::smatch match;
    if (std::regex_match(dirname, match, re)) {
        if (match.size() >= 3) {
            version = match[1];
            build = match[2];
            if (match.size() >= 4) {
                arch = match[3];
            }
            if (arch.size() == 0) {
                arch = "arm64e";
            }
            return true;
        }
    }
    return false;
}

void scan_dir_recursive(const std::string& basePath, const std::string& currentRelPath, std::vector<FileEntry>& entries) {
    std::string fullDirPath = basePath;
    if (!currentRelPath.empty()) fullDirPath += "/" + currentRelPath;

    DIR* dir = opendir(fullDirPath.c_str());
    if (!dir) {
        std::perror(("opendir " + fullDirPath).c_str());
        return;
    }

    struct dirent* entry;
    while ((entry = readdir(dir)) != nullptr) {
        std::string name = entry->d_name;
        if (name == "." || name == ".." || name[0] == '.')
            continue;

        std::string newRelPath = currentRelPath.empty() ? name : currentRelPath + "/" + name;

        std::string fullEntryPath = basePath + "/" + newRelPath;
        struct stat st;
        if (stat(fullEntryPath.c_str(), &st) != 0) {
            std::perror(("stat " + fullEntryPath).c_str());
            continue;
        }

        if (S_ISDIR(st.st_mode)) {
            scan_dir_recursive(basePath, newRelPath, entries);
        } else if (S_ISREG(st.st_mode)) {
            std::cout << "\tProcessing file: /" << newRelPath << std::endl;

            std::vector<SymbolEntry> symbols;
            bool gotSymbols = extract_symbols(fullEntryPath, symbols);
            std::sort(symbols.begin(), symbols.end(), [](const auto& a, const auto& b) {
                return a.address < b.address;
            });

            FileEntry fe;
            fe.name = name;
            // Remove "Symbols" prefix (assumes currentRelPath starts with "Symbols")
            fe.path = newRelPath.substr(7);
            fe.symbols = std::move(symbols);

            entries.push_back(std::move(fe));
        }
    }
    closedir(dir);
}

void write_sqlite_all(const std::string& db_path, const std::vector<std::tuple<std::string, std::string, std::string, std::vector<FileEntry>>>& all_data) {
    std::cout << "Writing data to '" << db_path << "'..." << std::endl;
    
    sqlite3* db;
    char* errMsg = nullptr;
    if (sqlite3_open(db_path.c_str(), &db) != SQLITE_OK) {
        std::cerr << "Can't open database: " << sqlite3_errmsg(db) << std::endl;
        throw std::invalid_argument("Can't open database: " + std::string(sqlite3_errmsg(db)));
    }
    
    // Enable extension loading (needed on some SQLite builds)
    sqlite3_enable_load_extension(db, 1);

//     // Load the compress extension, adjust path as needed
//     if (sqlite3_load_extension(db, "compress", 0, 0) != SQLITE_OK) {
//         std::cerr << "Failed to load compress extension: " << sqlite3_errmsg(db) << std::endl;
//         throw std::invalid_argument("Failed to load compress extension: " + sqlite3_errmsg(db));
//     }
//     
//     // Initialize compression (enables page compression for the database)
//     if (sqlite3_exec(db, "SELECT compress_init()", nullptr, nullptr, &errMsg) != SQLITE_OK) {
//         std::cerr << "Failed to init compression: " << errMsg << std::endl;
//         throw std::invalid_argument("Failed to init compression: " + errMsg);
//     }

    std::cout << "\tCreating tables..." << std::endl;
    const char* create_tables_sql = R"SQL(
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys = ON;
        
        CREATE TABLE IF NOT EXISTS builds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT,
            build TEXT,
            arch TEXT,
            UNIQUE(build, arch)
        );

        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            build_id INTEGER,
            name TEXT,
            path TEXT,
            FOREIGN KEY(build_id) REFERENCES builds(id),
            UNIQUE(build_id, name)
        );

        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER,
            address INTEGER,
            name TEXT,
            FOREIGN KEY(file_id) REFERENCES files(id),
            UNIQUE(file_id, address)
        );

        --CREATE INDEX IF NOT EXISTS idx_builds_build ON builds(build, arch);
        --CREATE INDEX IF NOT EXISTS idx_files_name ON files(name);
        --CREATE INDEX IF NOT EXISTS idx_files_build_id ON files(build_id);
        --CREATE INDEX IF NOT EXISTS idx_symbols_file_id ON symbols(file_id);
        --CREATE INDEX IF NOT EXISTS idx_symbols_address ON symbols(address);
    )SQL";
    if (sqlite3_exec(db, create_tables_sql, nullptr, nullptr, &errMsg) != SQLITE_OK) {
        std::cerr << "SQL error: " << errMsg << std::endl;
        throw std::invalid_argument("SQL error: " + std::string(errMsg));
    }

    sqlite3_stmt* stmt_insert_build = nullptr;
    sqlite3_prepare_v2(db, "INSERT OR IGNORE INTO builds(version, build, arch) VALUES (?, ?, ?);", -1, &stmt_insert_build, nullptr);
    sqlite3_stmt* stmt_get_build_id = nullptr;
    sqlite3_prepare_v2(db, "SELECT id FROM builds WHERE build = ? AND arch = ?;", -1, &stmt_get_build_id, nullptr);
    sqlite3_stmt* stmt_insert_file = nullptr;
    sqlite3_prepare_v2(db, "INSERT OR IGNORE INTO files(name, path, build_id) VALUES (?, ?, ?);", -1, &stmt_insert_file, nullptr);
    sqlite3_stmt* stmt_get_file_id = nullptr;
    sqlite3_prepare_v2(db, "SELECT id FROM files WHERE name = ? AND build_id = ?;", -1, &stmt_get_file_id, nullptr);
    sqlite3_stmt* stmt_insert_symbol = nullptr;
    sqlite3_prepare_v2(db, "INSERT OR IGNORE INTO symbols(name, address, file_id) VALUES (?, ?, ?);", -1, &stmt_insert_symbol, nullptr);

    for (const auto& [version, build, arch, files] : all_data) {
        std::cout << "\tWriting data for version " << version << " (" << build << ", " << arch << ")..." << std::endl;
        
        // Insert build
        sqlite3_bind_text(stmt_insert_build, 1, version.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt_insert_build, 2, build.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt_insert_build, 3, arch.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_step(stmt_insert_build);
        sqlite3_reset(stmt_insert_build);

        sqlite3_bind_text(stmt_get_build_id, 1, build.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt_get_build_id, 2, arch.c_str(), -1, SQLITE_TRANSIENT);
        int build_id = -1;
        if (sqlite3_step(stmt_get_build_id) == SQLITE_ROW) {
            build_id = sqlite3_column_int(stmt_get_build_id, 0);
        }
        sqlite3_reset(stmt_get_build_id);
        if (build_id == -1) {
            std::cerr << "Could not find `id` of build '" << build << "': " << sqlite3_errmsg(db) << std::endl;
            throw std::invalid_argument("Could not find `id` of build '" + build + "': " + sqlite3_errmsg(db));
        }

        for (const auto& f : files) {
            std::cout << "\t\tWriting symbols of '" << f.path << "'..." << std::endl;
            sqlite3_exec(db, "BEGIN TRANSACTION;", nullptr, nullptr, nullptr);
            
            sqlite3_bind_text(stmt_insert_file, 1, f.name.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_text(stmt_insert_file, 2, f.path.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_int(stmt_insert_file, 3, build_id);
            sqlite3_step(stmt_insert_file);
            sqlite3_reset(stmt_insert_file);
            
            sqlite3_bind_text(stmt_get_file_id, 1, f.name.c_str(), -1, SQLITE_TRANSIENT);
            sqlite3_bind_int(stmt_get_file_id, 2, build_id);
            int file_id = -1;
            if (sqlite3_step(stmt_get_file_id) == SQLITE_ROW) {
                file_id = sqlite3_column_int(stmt_get_file_id, 0);
            }
            sqlite3_reset(stmt_get_file_id);
            if (file_id == -1) {
                std::cerr << "Could not find `id` of file '" << f.name << "': " << sqlite3_errmsg(db) << std::endl;
                throw std::invalid_argument("Could not find `id` of file '" + f.name + "': " + sqlite3_errmsg(db));
            }

            for (const auto& s : f.symbols) {
                sqlite3_bind_text(stmt_insert_symbol, 1, s.name.c_str(), -1, SQLITE_TRANSIENT);
                sqlite3_bind_int64(stmt_insert_symbol, 2, static_cast<sqlite3_int64>(s.address));
                sqlite3_bind_int(stmt_insert_symbol, 3, file_id);
                sqlite3_step(stmt_insert_symbol);
                sqlite3_reset(stmt_insert_symbol);
            }
            
            sqlite3_exec(db, "COMMIT;", nullptr, nullptr, nullptr);
            //std::cout << "\t\tSymbols of '" << f.path << "' complete" << std::endl;
        }
        std::cout << "\tVersion " << version << " (" << build << ") complete" << std::endl;
    }
    
    std::cout << "Closing database..." << std::endl;
    sqlite3_finalize(stmt_insert_build);
    sqlite3_finalize(stmt_get_build_id);
    sqlite3_finalize(stmt_insert_file);
    sqlite3_finalize(stmt_get_file_id);
    sqlite3_finalize(stmt_insert_symbol);
    sqlite3_exec(db, "PRAGMA wal_checkpoint(TRUNCATE);", nullptr, nullptr, nullptr);
    sqlite3_close(db);
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <directory-with-symbols> [path-to-swift-demangle-binary]" << std::endl;
        return 1;
    }
    
    std::string parentDir = argv[1];
    std::string swiftDemanglePath = "";
    if (argc >= 3) {
        swiftDemanglePath = argv[2];
    }

    DIR* dir = opendir(parentDir.c_str());
    if (!dir) {
        std::perror(("opendir " + parentDir).c_str());
        return 1;
    }

    // Regex to parse directory names like: iPhone14,3 18.5 (22F76)
    std::regex dirRegex(R"(^(?:|.* )([0-9]+(?:\.[0-9]+)*) \(([^)]+)\)(?: (arm64e?))?$)");
    
    if (swiftDemanglePath != "") {
        int master_fd = 0;
        swift_demangler_pid = forkpty(&master_fd, NULL, NULL, NULL);;
        if (swift_demangler_pid != -1) {
            if (swift_demangler_pid == 0) {
                char* const envp[] = {
                    (char*)"LD_LIBRARY_PATH=./",
                    nullptr
                };
                execle(swiftDemanglePath.c_str(), "swift-demangle", (char*)nullptr, envp);
                perror("execl");
                exit(1);
            }
            else
            {
                swift_demangler_stdin = fdopen(master_fd, "w");
                setvbuf(swift_demangler_stdin, NULL, _IONBF, 0);
                swift_demangler_stdout = fdopen(master_fd, "r");
                setvbuf(swift_demangler_stdout, NULL, _IONBF, 0);
            }
        }
        else
            perror("Error forking");
    }

    std::vector<std::tuple<std::string, std::string, std::string, std::vector<FileEntry>>> all_data;
    struct dirent* entry;
    while ((entry = readdir(dir)) != nullptr) {
        std::string name = entry->d_name;
        if (name == "." || name == ".." || name[0] == '.')
            continue;

        std::string fullPath = parentDir + "/" + name;

        struct stat st;
        if (stat(fullPath.c_str(), &st) != 0) {
            std::perror(("stat " + fullPath).c_str());
            continue;
        }

        if (!S_ISDIR(st.st_mode))
            continue;

        // Parse version and build
        std::string version, build, arch;
        if (!parse_dirname(name, version, build, arch, dirRegex)) {
            std::cerr << "Skipping directory (no version/build match): " << name << std::endl;
            continue;
        }

        std::cout << "Scanning directory: " << name << " (version: " << version << ", build: " << build << ", architecture: " << arch << ")" << std::endl;

        // Symbols subdirectory path
        std::string symbolsDir = fullPath + "/Symbols";

        // Check if Symbols directory exists
        struct stat stSymbols;
        if (stat(symbolsDir.c_str(), &stSymbols) != 0 || !S_ISDIR(stSymbols.st_mode)) {
            std::cerr << "Symbols directory missing or invalid: " << symbolsDir << std::endl;
            continue;
        }

        // Collect files with symbols
        std::vector<FileEntry> files;
        scan_dir_recursive(fullPath, "Symbols", files);
        all_data.emplace_back(version, build, arch, std::move(files));
    }
    closedir(dir);
    
    if (swift_demangler_pid) {
        if (swift_demangler_stdin) {
            fwrite("\n", 1, 1, swift_demangler_stdin);      //unblock waiting child
            fclose(swift_demangler_stdin);
        }
        if (swift_demangler_stdout) {
            fclose(swift_demangler_stdout);
        }
        int status = 0;
        waitpid(swift_demangler_pid, &status, 0);
        if (WIFEXITED(status)) {
            if (WEXITSTATUS(status) != 0) {
                std::cerr << "swift-demangle exited with code " << WEXITSTATUS(status) << std::endl;
            }
        } else {
            std::cerr << "swift-demangle terminated abnormally" << std::endl;
        }
    }
    
    // write results to database
    write_sqlite_all("symbols.db", all_data);

    return 0;
}
