import json
import zlib
import hashlib

from PyQt5 import QtCore
from PyQt5 import QtNetwork

from LogViewer.storage import SettingsSingleton

try:
    from Cryptodome.Cipher import AES   # pycryptodomex
except ImportError as e:
    from Crypto.Cipher import AES       # pycryptodome

from shared.utils import catch_exceptions

import logging
logger = logging.getLogger(__name__)

class UdpServer(QtNetwork.QUdpSocket):
    newMessage = QtCore.pyqtSignal(list)

    def __init__(self, key, /, host="::", port=5555):
        super(UdpServer, self).__init__()
        # init state
        self.last_counter = None
        self.last_processID = None
        
        # "derive" 256 bit key
        encryptedKey = hashlib.sha256()
        encryptedKey.update(bytes(key, "UTF-8"))
        self.key = encryptedKey.digest()

        hostAddress = QtNetwork.QHostAddress()
        hostAddress.setAddress(host)

        self.udpSocket = QtNetwork.QUdpSocket(self)
        self.udpSocket.bind(hostAddress, port)

        self.udpSocket.readyRead.connect(self.readPendingDatagrams)

    def __del__(self):
        self.stop()
    
    def stop(self):
        self.udpSocket.close()
        self.udpSocket = None
    
    @catch_exceptions(logger=logger)
    @QtCore.pyqtSlot()
    def readPendingDatagrams(self):
        newEntries = []
        while self.udpSocket.hasPendingDatagrams():
            logger.debug("udp listener thread started")

            payload, host, port = self.udpSocket.readDatagram(self.udpSocket.pendingDatagramSize())

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
                return
            
            # decompress raw data
            payload = zlib.decompress(payload, zlib.MAX_WBITS | 16)
            
            # decode raw json encoded data
            decoded = json.loads(str(payload, "UTF-8"))
            
            # emit status entries
            correctedProcessId = self.correctProcessId(self.last_processID, decoded["tag"]["processID"])
            if correctedProcessId != None:
                newEntries.append(correctedProcessId)

            if self.last_counter != None and decoded["tag"]["counter"] != self.last_counter + 1:
                message = "Stream counter jumped from %d to %d leaving out %d lines" % (self.last_counter, decoded["tag"]["counter"], decoded["tag"]["counter"] - self.last_counter - 1)
                newEntries.append({
                    #"__warning": True,
                    "__virtual": True,
                    "__message": message,
                    "timestamp": "",
                })
                
            newEntries.append(decoded)
        
            # update state
            self.last_processID = decoded["tag"]["processID"]
            self.last_counter = decoded["tag"]["counter"]
        
        logger.debug("udp listener thread stopped")
        self.newMessage.emit(newEntries)
    
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
