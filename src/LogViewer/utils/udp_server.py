import sys
import socket
import select
import ipaddress
import json
import zlib
import hashlib
from threading import Thread, current_thread
import weakref

from PyQt5 import QtCore

from LogViewer.storage import SettingsSingleton

try:
    from Cryptodome.Cipher import AES   # pycryptodomex
except ImportError as e:
    from Crypto.Cipher import AES       # pycryptodome

from shared.utils import catch_exceptions

import logging
logger = logging.getLogger(__name__)

class UdpServer(QtCore.QObject):
    newMessage = QtCore.pyqtSignal(list)

    def __init__(self, key, /, host="::", port=5555):
        super(UdpServer, self).__init__()
        
        # init state
        self.run = False
        self.last_counter = None
        self.last_remote = None
        weakref.finalize(self, self.stop)
        
        # "derive" 256 bit key
        m = hashlib.sha256()
        m.update(bytes(key, "UTF-8"))
        self.key = m.digest()
        
        # create listening udp socket and process all incoming packets
        self.sock = socket.socket(socket.AF_INET6 if ipaddress.ip_address(host).version==6 else socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.setblocking(0)
        
        # start receiver thread
        self.run = True
        self.listener_thread = Thread(name="rawlog_stream_listener", target=self._thread, daemon=True)
        self.listener_thread.start()
    
    def __del__(self):
        self.stop()
    
    def stop(self):
        if self.run:
            logger.debug("Stopping UDP listener thread...")
            self.run = False
            logger.debug("Waiting for UDP listener thread to stop...")
            if self.listener_thread != current_thread() and self.listener_thread.is_alive():
                self.listener_thread.join(1.0)
        if self.sock != None:
            logger.debug("Closing UDP listener socket...")
            self.sock.close()
            self.sock = None
    
    def getLastRemote(self):
        return self.last_remote;
    
    @catch_exceptions(logger=logger)
    def _thread(self):
        logger.debug("UDP listener thread started")
        while self.run:
            # Loop until something happens, but use select because we don't want to busy-wait
            while self.run:
                readable, writable, exceptional = select.select([self.sock], [], [self.sock], 0.5)
                if self.sock in readable or self.sock in exceptional:
                    break
            # handle all pending udp packets in a row using our non-blocking socket
            logger.debug("Select returned our socket, now handling newly queued UDP packets...")
            newEntries = []
            while self.run:
                try:
                    logger.debug("Trying to read next udp packet...")
                    if self.sock in readable:
                        payload, client_address = self.sock.recvfrom(65536)
                        self.last_remote = client_address
                    if self.sock in exceptional:
                        self.stop()
                        break        # leave this loop, self-run == False now
                except (socket.timeout, InterruptedError) as e:
                    continue
                except BlockingIOError:
                    break
                except:
                    raise
                
                # decrypt raw data
                try:
                    payload = self._decrypt(payload)
                except Exception as e:
                    message = "Decryption of %d bytes failed: %s" % (len(payload), str(e))
                    newEntries.append({
                        #"__warning": True,
                        "__virtual": True,
                        "__message": message,
                    })
                    continue        # process next udp packet
                
                # decompress raw data
                payload = zlib.decompress(payload, zlib.MAX_WBITS | 16)
                
                # decode raw json encoded data
                decoded = json.loads(str(payload, "UTF-8"))
                
                if "tag" in decoded and "counter" in decoded["tag"]:
                    if self.last_counter != None and decoded["tag"]["counter"] != self.last_counter + 1:
                        message = "Stream counter jumped from %d to %d leaving out %d lines" % (self.last_counter, decoded["tag"]["counter"], decoded["tag"]["counter"] - self.last_counter - 1)
                        newEntries.append({
                            #"__warning": True,
                            "__virtual": True,
                            "__message": message,
                        })

                    # update state
                    self.last_counter = decoded["tag"]["counter"]
                
                # emit logentry itself
                newEntries.append(decoded)
                
                # emit at max 50 entries in one signal to make our ui more responsive
                if len(newEntries) >= 50:
                    break
            
            if len(newEntries) > 0:
                logger.debug(f"Emitting {len(newEntries)} new rows from UDP listener...")
                self.newMessage.emit(newEntries)
                logger.debug(f"Done emitting entries")
                
        logger.debug("UDP listener thread stopped")
    
    def _decrypt(self, ciphertext):
        iv = ciphertext[:12]
        if len(iv) != 12:
            raise Exception("Cipher text is damaged: invalid iv length")

        tag = ciphertext[12:28]
        if len(tag) != 16:
            raise Exception("Cipher text is damaged: invalid tag length")

        encrypted = ciphertext[28:]

        # Construct AES cipher, with old iv.
        cipher = AES.new(self.key, AES.MODE_GCM, iv)

        # Decrypt and verify.
        try:
            plaintext = cipher.decrypt_and_verify(encrypted, tag)
        except ValueError as e:
            raise Exception("Cipher text is damaged: {}".format(e))
        return plaintext
