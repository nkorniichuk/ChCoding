from ETCP import *
import time

send = ETCP()
start = time.time()
print 'Started at: ',start
send.sendFile('test2.txt')
end = time.time()
print 'Finished at: ',end
print 'Duration: ',end - start

