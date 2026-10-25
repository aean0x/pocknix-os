# pocknix_cdp - Steam's CEF debugging port (8080, opened by the launchers), for scripts that
# drive Steam's UI from outside it.
import base64
import json
import os
import socket
import struct
import urllib.request

CDP = "http://127.0.0.1:8080/json/list"


class WebSocket:
    """Just enough RFC 6455 for one CDP exchange: the base image ships no websocket module."""

    def __init__(self, url: str, timeout: float):
        hostport, path = url[len("ws://"):].split("/", 1)
        host, port = hostport.rsplit(":", 1)
        self.s = socket.create_connection((host, int(port)), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
                        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                        "Sec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            head += self._exact(1)
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError(head.split(b"\r\n", 1)[0].decode(errors="replace"))

    def _exact(self, n: int) -> bytes:
        b = b""
        while len(b) < n:
            c = self.s.recv(n - len(b))
            if not c:
                raise ConnectionError("connection closed")
            b += c
        return b

    def send(self, text: str) -> None:
        data, mask = text.encode(), os.urandom(4)
        n = len(data)
        if n < 126:
            hdr = bytes([0x81, 0x80 | n])
        elif n < 65536:
            hdr = bytes([0x81, 0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr = bytes([0x81, 0x80 | 127]) + struct.pack(">Q", n)
        self.s.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self) -> str:
        msg = b""
        while True:
            b0, b1 = self._exact(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._exact(8))[0]
            payload, op = self._exact(n), b0 & 0x0F
            if op == 0x8:
                raise ConnectionError("closed by Steam")
            if op in (0x9, 0xA):
                continue
            msg += payload
            if b0 & 0x80:
                return msg.decode()


def target() -> str | None:
    try:
        with urllib.request.urlopen(CDP, timeout=3) as r:
            for t in json.load(r):
                if t.get("title") == "SharedJSContext":
                    return t["webSocketDebuggerUrl"]
    except (OSError, ValueError):
        pass
    return None


def evaluate(url: str, js: str, timeout: float = 60):
    ws = WebSocket(url, timeout)
    try:
        ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                            "params": {"expression": js, "awaitPromise": True, "returnByValue": True}}))
        while True:
            r = json.loads(ws.recv())
            if r.get("id") == 1:
                res = r.get("result", {})
                if "exceptionDetails" in res:
                    raise RuntimeError(res["exceptionDetails"].get("exception", {}).get("description", "JS exception"))
                return res.get("result", {}).get("value")
    finally:
        ws.s.close()
