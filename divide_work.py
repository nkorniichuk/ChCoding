import os
from struct import *
from socket import *
import sys
import time 

ACK_BYTE = 200
NACK_HEAD_BYTE = 300
FIRST_HEAD_BYTE = 100

class ETCP():
	def __init__(self, win_size = 256, pack_size = 1400, debug = True, host = '192.168.7.2'):
	        
                self.window_size = win_size
		self.packet_size = pack_size
                
                self.curPos = 0

                self.debug = debug # for testing on local machine

		self.dir_port = 5000
                self.back_port = 5001
		
                self.dst_host = host #host to send to
                
		self.dir_ch = ''
            
                self.back_ch = ''

                self.back_ch_conn = ''

	def sendFile(self, filename):

                fileInfo = os.stat(filename)
                
                #try:    
                self.dir_ch = socket(AF_INET, SOCK_DGRAM)
                self.dir_ch.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                self.dir_ch.setsockopt(SOL_SOCKET, SO_RCVBUF, 800000)
                self.dir_ch.setsockopt(SOL_SOCKET, SO_SNDBUF, 800000)
                self.back_ch = socket(AF_INET, SOCK_STREAM)
                self.back_ch.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                self.back_ch.bind(('0.0.0.0',self.back_port))
                self.back_ch.connect((self.dst_host,self.back_port))
                    
                #except:
                #    if self.debug:
                #        print 'ERROR::ERROR OCCURED WHILE SOCKET ESTABLISHING'
                #    self._close()
                #    sys.exit()
	        
                self._firstTCP(filename, fileInfo)

		windowsNumber = fileInfo.st_size/(self.window_size*self.packet_size) \
				if fileInfo.st_size%(self.window_size*self.packet_size) == 0 \
				else fileInfo.st_size/(self.window_size*self.packet_size) +1
		
		
	        print str(windowsNumber)

                with open(filename, 'r') as file:
                    #curPos = 0

		    for i in range(1,windowsNumber+1):
                        #    curWinSize = self.window_size if i < windowsNumber or \
                         #           fileInfo.st_size%(self.window_size*self.packet_size) == 0 \
                          #          else fileInfo.st_size/self.packet_size if fileInfo.st_size/self.packet_size > 0 \
                        curWinSize = 0

                        if i < windowsNumber or fileInfo.st_size%(self.window_size*self.packet_size) == 0:
                            curWinSize = self.window_size
                        else:
                            if fileInfo.st_size%(self.window_size*self.packet_size)/self.packet_size > 0:
                                if (fileInfo.st_size%(self.window_size*self.packet_size))%self.packet_size == 0:
                                    curWinSize = (fileInfo.st_size%(self.window_size*self.packet_size))/self.packet_size
                                else:
                                    curWinSize = (fileInfo.st_size%(self.window_size*self.packet_size))/self.packet_size + 1
                            else:
                                curWinSize = 1
                                    
    	       	        snd_buffer = self._chunky(file, curWinSize)
#                            print str(curPos)
                        self._sendWin(snd_buffer,curWinSize)
                self.curPos = 0
                self._close() 

        def _firstTCP(self, filename, fileInfo):
                data = filename+':'+str(fileInfo.st_size)
                message = bytearray([FIRST_HEAD_BYTE,len(data)])+data
                read = self.back_ch.send(message)
                if self.debug:
                    if read == 0:
                        print 'ERROR::ERROR OCCURED WHILE SENDING FIRST TCP MSG'
                    else:
                        print 'INFO::INIT TCP PACKET SENT'
	
        def _chunky(self, File, CurWinSize):
                array = []
		File.seek(self.curPos)
		for i in range(0,CurWinSize):

	                chunk = File.read(self.packet_size)
			if chunk=='':
				break
			elif len(chunk) <= self.packet_size:
				array.append(chunk)
				array[i] = pack('>H',i)+array[i]

        	self.curPos = File.tell()
#                print str(curPos)
    	        return array
	
        def _sendWin(self, window, curWinSize, repeat = []):                
                rng = repeat if len(repeat) > 0 else range(0,curWinSize)
                
                for i in rng:
                    try:
                        self.dir_ch.sendto(window[i], (self.dst_host, self.dir_port))
                        time.sleep(0.005)
                    except:
                        if self.debug:
                            print 'ERROR::ERROR OCCURED WHILE SENDING ', str(i), ' MESSAGE'
                
                if self.debug:
                    print 'INFO::WAITING FOR NACK OR ACK'
                
                nack = self._recvNack()

                if len(nack) == 0:
                    if self.debug:
                        print 'INFO::ACK RECEIVED'
                    return 0
                else:
                    if self.debug:
                        print 'INFO::GROUP NACK RECEIVED TRYING TO RESEND...'
                    return self._sendWin(window, curWinSize, nack)


        def _recvNack(self):

                nack = []
                head = self.back_ch.recv(2)
                head = unpack('>H',head)[0]
                if head == NACK_HEAD_BYTE:
                    if self.debug:
                        print 'INFO::NACK RECEIVED'
                    length = unpack('>H',self.back_ch.recv(2))[0]
                    nack = self.back_ch.recv(length).split(',')
                elif head == ACK_BYTE:
                    if self.debug:
                        print 'INFO::WINDOW RECEIVED'
                else:
                    if self.debug:
                        print 'ERROR::UNKNOWN ACK TYPE'
                return nack
            

                



######################----------------_########################
        




        def receive(self):
                #try:
                self.dir_ch = socket(AF_INET,SOCK_DGRAM)
                self.dir_ch.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                self.dir_ch.setsockopt(SOL_SOCKET, SO_RCVBUF, 716800)
                self.dir_ch.bind(('0.0.0.0',self.dir_port))
                self.back_ch = socket(AF_INET,SOCK_STREAM)
                self.back_ch.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                self.back_ch.bind(('0.0.0.0',self.back_port))
                self.back_ch.listen(1)

                self.back_ch_conn , addr = self.back_ch.accept()

                #except:
                #    if self.debug:
                #        print 'ERROR::ERROR OCCURED WHILE SOCKET ESTABLISHING'
                #    self._close()
                #    sys.exit()

                head = self.back_ch_conn.recv(1)

                if ord(head) == FIRST_HEAD_BYTE:
                    if self.debug:
                        print 'INFO::INIT MESSAGE RECEIVED'
                else:
                    if self.debug:
                        print 'ERROR::UNKNOWN MESSAGE'
                    self._close()
                    sys.exit()

                length = ord(self.back_ch_conn.recv(1))
                data = self.back_ch_conn.recv(length)
                data = data.split(':')

                if self.debug:
                    print 'INFO::Filename: ',data[0],'; Size: ',data[1]

                #try:
                with open(data[0],'w+') as f:
                    windowsNumber = int(data[1])/(self.window_size*self.packet_size) \
                            if int(data[1])%(self.window_size*self.packet_size) == 0 \
                            else int(data[1])/(self.window_size*self.packet_size) + 1
                    print str(windowsNumber)       
                    for i in range(1,windowsNumber+1):
                        curWinSize = 0

                        if i < windowsNumber or int(data[1])%(self.window_size*self.packet_size) == 0:
                            curWinSize = self.window_size
                        else:
                            if (int(data[1])%(self.window_size*self.packet_size))/self.packet_size > 0:
                                if (int(data[1])%(self.window_size*self.packet_size))%self.packet_size == 0:
                                    curWinSize = (int(data[1])%(self.window_size*self.packet_size))/self.packet_size
                                else:
                                    curWinSize = (int(data[1])%(self.window_size*self.packet_size))/self.packet_size + 1
                            else:
                                curWinSize = 1
                        
                        
                       # if i < windowsNumber or \
                        #        int(data[1])%(self.window_size*self.packet_size) == 0 \
                         #       else (int(data[1])%(self.window_size*self.packet_size))/self.packet_size \
                          #      if (int(data[1])%(self.window_size*self.packet_size))/self.packet_size > 0 else 1
                        
                        rcv_win = [None]*curWinSize
                        self._recvWin(rcv_win,f)

                #except:
                #    if self.debug:
                #        print 'ERROR::ERROR OCCURED WHILE WRITING TO FILE'
                #    self._close()
                #    sys.exit()

                self._close()

        def _close(self):
                    print 'CLEANING!'
                #try:
                    self.dir_ch.close()
                    print 'dir'
                    self.back_ch.close()
                    print 'back'
                    if self.back_ch_conn != '':
                        self.back_ch_conn.close()
                        print 'back_ch_conn'
                #except:
#                    pass


        def _recvWin(self, window, File, repeat = []):
                rng = repeat if len(repeat) > 0 else range(0,len(window))
                print 'rcv start'
                print rng
                for i in rng:
                    data  = self.dir_ch.recv(2+self.packet_size)
                    _id = unpack('>H',data[0:2])[0]
                    #data = data[2:]
                    print str(i)
                    
                    window[_id] = data[2:]
                nack = self._checkWin(window)
                
                if len(nack):
                    if self.debug:
                        print 'INFO::NOT EVERYTHING RECEIVED CORRCTLY'
                    self._sendNack(nack)
                    return self._recvWin(window,nack)
                else:
                    for i in range(0,len(window)):
                        File.write(window[i])
                    if self.debug:
                        print 'INFO::WINDOW IS RECEIVED AND WRITTEN TO THE FILE'
                    return self._sendAck()

        def _checkWin(self,window):
                nack_arr = []
                for i in range(0,len(window)):
                    if window[i] == None:
                        nack_arr.append(i)
                    else:
                        continue
                return nack_arr


        def _sendAck(self):
                ack_msg = pack('>H',ACK_BYTE)
                self.back_ch_conn.send(ack_msg)

        def _sendNack(self, nack):
                NACK = pack('>H',NACK_HEAD_BYTE)+pack('>H',len(str(nack))-2)+str(nack)[1:-1]
                self.back_ch_conn.send(NACK)
