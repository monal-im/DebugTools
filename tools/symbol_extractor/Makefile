MAKEFLAGS += --quiet
BINS=symbol_extractor

all: $(BINS)

%: %.cpp
	echo "[G++]	$@"
	g++ -std=c++20 -ggdb -o $@ $< -lc++abi -lsqlite3

clean:
	echo "[CLEAN]	$(BINS)"
	-rm $(BINS) 2>/dev/null

.PHONY: clean all
