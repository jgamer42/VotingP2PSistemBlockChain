import zmq
import random
import json
import os
import sys
from dotenv import load_dotenv
import socket as sok
import argparse

load_dotenv()
PRINCIPAL_PATH = os.getenv('PRINCIPAL_PATH')
UPLOAD_TYPE = os.getenv('UPLOAD_TYPE')
DOWNLOAD_TYPE = os.getenv('DOWNLOAD_TYPE')
SUCCESS_CODE = os.getenv('SUCCESS_CODE')
MAX_RANGE = int(os.getenv('MAX_RANGE'))
FIND_POSITION_TYPE = os.getenv('FIND_POSITION_TYPE')
CONFIRM_SUSCRIPTION = os.getenv('CONFIRM_SUSCRIPTION')
CONFIRM_SUSCRIPTION = os.getenv('CONFIRM_SUSCRIPTION')
SEND_TYPE = os.getenv('SEND_TYPE')

sys.path.insert(0, PRINCIPAL_PATH)
from Util import header, subscribe, socketsRepo, broker
context = zmq.Context()
preNode = ""
posNode = ""
responsabilityRange = (0,MAX_RANGE)

def getMyIP():  
    s = sok.socket(sok.AF_INET, sok.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    IPAddr = s.getsockname()[0]
    return IPAddr

def getMyID(): 
    return random.randint(0, MAX_RANGE)

def getPosition(socket,responsability, heade):
    if heade["OperationType"] == FIND_POSITION_TYPE:
        subscribe.getPosition(socket,responsability, heade["MyId"], preNode, posNode, heade["Address"])

def confirmPosition(socket, heade, directory, myAddress):
    global preNode, posNode, responsabilityRange
    if heade["OperationType"] == CONFIRM_SUSCRIPTION: 
        preNode = heade["Address"]
        responsabilityRange = (heade["MyId"], responsabilityRange[1])
        hs = header.checkAllGood()
        headerJSON = json.dumps(hs).encode()
        socket.send_multipart([headerJSON])

        #enviando lo que ya no esta en mi tramo
        files = os.listdir(directory)
        for i in files:
            fileID = int(i,16)%MAX_RANGE
            if not subscribe.isIn(responsabilityRange, fileID):
                socketsub, _, _, _ = subscribe.findPosition(heade["Address"], myAddress, fileID)
                fileSize = os.path.getsize(f"{directory}{i}")
                with open(f'{directory}{i}', 'rb') as inputFile:
                    bytes = inputFile.read()
                    broker.sendChunk(bytes, socketsub, i, fileSize, 0, i)
                os.remove(f'{directory}{i}')

def savePart(socket, heade, binaryFile, directory):
    if heade["OperationType"] == SEND_TYPE :
        hash = heade["Hash"]
        fileName = heade["Name"]
        print(f"upload file: {fileName} hash: {hash}")
        message = socketsRepo.saveFile(hash, binaryFile, dirNode=directory)
        socket.send(message.encode())

def download(socket, heade, directory):
    if heade["OperationType"] == DOWNLOAD_TYPE:
        fileName = heade["Name"]
        hs = header.createHeader(fileName, DOWNLOAD_TYPE, dirnode=directory)
        hsJSON = json.dumps(hs).encode()
        socketsRepo.sendFile(socket, fileName, hsJSON, dirNode=directory)

def main():
    global preNode, posNode, responsabilityRange

    parser = argparse.ArgumentParser(
        description='Example with nonoptional arguments',
    )

    parser.add_argument('-address', action="store", type=str, default="localhost:0000")
    parser.add_argument('-port', action="store", type=str)
    parser.add_argument('--firstNode', action="store_true", default=False)
    data = parser.parse_args()
    print(data.firstNode)
    portra = data.port
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{portra}")
    myAddress = f"{getMyIP()}:{portra}"

    firtsNode = f"{data.address}" if not data.firstNode else myAddress
    print("FirstNode-> ", firtsNode)
    print("My Address-> ", myAddress)
    preNode = myAddress
    preNodeSocket = 0
    posNode = myAddress
    myID = getMyID()
    print("My ID-> ", myID)
    responsabilityRange = (myID, myID)
    mainPath = os.path.dirname(os.path.realpath(__file__))
    directory = f"Files/{myID}/"
    dirpath = os.path.join(mainPath, directory)
    os.mkdir(dirpath)
    
    if not data.firstNode: 
        socketPreNode, posNode, preNode, preNodeId= subscribe.findPosition(firtsNode, myAddress, myID)
        responsabilityRange = (preNodeId, myID) 
        
        #Falta enviar todos los paquetes que pertenecen al nuevo tramo

        # confirm pos
        hs = header.confirmSubscription(myAddress, myID)
        headerJSON = json.dumps(hs).encode()
        socketPreNode.send_multipart([headerJSON, headerJSON])

        message = json.loads(socketPreNode.recv())
        print(message)
    
    while True: 
        print(myAddress, myID, preNode, posNode, responsabilityRange)
        headerJSON, binaryFile = socket.recv_multipart()
        heade = json.loads(headerJSON)
        print(heade)

        print(heade["OperationType"])
        menu = {
            FIND_POSITION_TYPE: getPosition(socket,responsabilityRange, heade),
            CONFIRM_SUSCRIPTION: confirmPosition(socket, heade, directory, myAddress),
            SEND_TYPE: savePart(socket, heade, binaryFile, directory),
            DOWNLOAD_TYPE: download(socket, heade, directory)

        }

        menu[heade["OperationType"]]

main()