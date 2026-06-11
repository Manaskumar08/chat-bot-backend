import websocket
import threading
import queue
import time

WS_URL = 'ws://localhost:8001/voice-chat/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6Im1hbmFzQGdtYWlsLmNvbSIsImV4cCI6MTc4MDU1Mzg3NSwiaWF0IjoxNzgwNTUyMDc1fQ.7MahwSSOmeDH2fUCGYdOsUBzrYYInqotu6Olt2FU8DM'
q = queue.Queue()
ws = websocket.WebSocket()
ws.connect(WS_URL)
print('connected')

def sender():
    while True:
        data = q.get()
        if data is None:
            break
        try:
            print('sending', len(data))
            ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
        except Exception as e:
            print('send error', repr(e))
            break

threading.Thread(target=sender, daemon=True).start()
q.put(b'test1234')
q.put(None)
time.sleep(2)
print('done')
