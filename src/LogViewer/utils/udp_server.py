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

try:
    from Cryptodome.Cipher import AES   # pycryptodomex
except ImportError as e:
    from Crypto.Cipher import AES       # pycryptodome

from shared.utils import catch_exceptions

import logging
logger = logging.getLogger(__name__)

class UdpServer(QtCore.QObject):
    newMessage = QtCore.pyqtSignal(list)

    def __init__(self, queue, key, /, host="::", port=5555):
        super(UdpServer, self).__init__()
        # init state
        self.run = False
        self.queue = queue
        self.last_counter = None
        self.last_processID = None
        weakref.finalize(self, self.stop)
        
        # "derive" 256 bit key
        m = hashlib.sha256()
        m.update(bytes(key, "UTF-8"))
        self.key = m.digest()
        
        # create listening udp socket and process all incoming packets
        self.sock = socket.socket(socket.AF_INET6 if ipaddress.ip_address(host).version==6 else socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        
        # start receiver thread
        self.run = True
        self.listener_thread = Thread(name="rawlog_stream_listener", target=self._thread, daemon=True)
        self.listener_thread.start()

    def __del__(self):
        self.stop()
    
    def stop(self):
        if self.run:
            logger.debug("stopping udp listener thread")
            self.run = False
            logger.debug("waiting for udp listener thread to stop")
            if self.listener_thread != current_thread() and self.listener_thread.is_alive():
                self.listener_thread.join(4.0)
        if self.sock != None:
            logger.debug("closing udp listener socket")
            self.sock.close()
            self.sock = None
    
    @catch_exceptions(logger=logger)
    def _thread(self):
        logger.debug("udp listener thread started")
        while self.run:
            try:
                readable, writable, exceptional = select.select([self.sock], [], [self.sock], 0.5)
                if self.sock not in readable and self.sock not in exceptional:
                    continue
                if self.sock in readable:
                    payload, client_address = self.sock.recvfrom(65536)
                if self.sock in exceptional:
                    self.stop()
                    continue        # leave this loop, self-run == False now
            except (socket.timeout, InterruptedError):
                continue
            except:
                raise
            
            # decrypt raw data
            try:
                payload = self._decrypt(payload)
            except Exception as e:
                message = "Decryption of %d bytes failed: %s" % (len(payload), str(e))
                self.queue.put({
                    #"__warning": True,
                    "__virtual": True,
                    "__message": message,
                })
                continue        # process next udp packet
            
            # decompress raw data
            payload = zlib.decompress(payload, zlib.MAX_WBITS | 16)
            
            # decode raw json encoded data
            decoded = json.loads(str(payload, "UTF-8"))


            # move emit status entries to rawlog -> that this doesnt have to be synthesize
            
            # emit status entries
            self.queue.put(self.correctProcessId(self.last_processID, decoded["tag"]["processID"]))

            if self.last_counter != None and decoded["tag"]["counter"] != self.last_counter + 1:
                message = "Stream counter jumped from %d to %d leaving out %d lines" % (self.last_counter, decoded["tag"]["counter"], decoded["tag"]["counter"] - self.last_counter - 1)
                self.queue.put({
                    #"__warning": True,
                    "__virtual": True,
                    "__message": message,
                })
            
            # emit logentry itself
            self.queue.put(decoded)
            
            # update state
            self.last_processID = decoded["tag"]["processID"]
            self.last_counter = decoded["tag"]["counter"]
        logger.debug("udp listener thread stopped")
    
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

    def correctProcessId(self, last_processID, decoded):
        if last_processID != None and decoded != last_processID:
            message = "Processid changed from %s to %s..." % (last_processID, decoded)
            return {
                #"__warning": True,
                "__virtual": True,
                "__message": message,
            }
