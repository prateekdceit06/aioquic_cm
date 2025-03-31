import argparse
import asyncio
import logging
from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived, StreamReset, ProtocolNegotiated

from log_config import setup_logging


class ContinuousFileClientProtocol(QuicConnectionProtocol):
    """
    Subclass QuicConnectionProtocol so we can:
      1. open a stream,
      2. send data (filename),
      3. receive file chunks in quic_event_received() until the stream ends,
      4. remain active until the entire file is received (or the connection closes).
    """
    def __init__(self, *args, message: bytes, done_event: asyncio.Future, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message
        self.done_event = done_event
        self.stream_id = None
        self.file_data = bytearray()

    def connection_made(self, transport):
        """Called when the connection is established."""
        super().connection_made(transport)
        # Get a new bidirectional stream ID, and send our request
        self.stream_id = self._quic.get_next_available_stream_id()
        self._quic.send_stream_data(self.stream_id, self.message, end_stream=True)
        logging.info(f"Sending file request: {self.message.decode()}")

    def quic_event_received(self, event):
        """Called whenever a QUIC event occurs."""
        # You can watch for ProtocolNegotiated to see any ALPN or version details:
        if isinstance(event, ProtocolNegotiated):
            logging.debug(f"Negotiated ALPN: {event.alpn_protocol}")

        if isinstance(event, StreamDataReceived):
            if event.stream_id == self.stream_id:
                logging.debug(f"Received chunk ({len(event.data)} bytes) from stream {event.stream_id}")
                self.file_data.extend(event.data)

                if event.end_stream:
                    # The server signaled end of the stream
                    logging.info(f"Finished receiving file. Total size: {len(self.file_data)} bytes")
                    # Convert to string if you want
                    # or write to a file, etc.
                    if not self.done_event.done():
                        self.done_event.set_result(True)

        # If the server reset our stream for some reason
        if isinstance(event, StreamReset):
            if event.stream_id == self.stream_id:
                logging.error(f"Stream {event.stream_id} reset by peer!")
                if not self.done_event.done():
                    self.done_event.set_result(False)


async def run_client(log_level, filename, host, port):
    setup_logging(log_file="cm_client.log", level=log_level)

    config = QuicConfiguration(is_client=True)
    # Disable cert verification for testing with self-signed cert
    config.verify_mode = False
    # Must match your certificate’s common name (CN) or subjectAltName
    config.server_name = host

    # We'll signal this future once the response is fully received
    done_event = asyncio.get_event_loop().create_future()

    # Prepare the bytes message (file name)
    message = filename.encode()

    def protocol_factory(*args, **kwargs):
        return ContinuousFileClientProtocol(
            *args,
            message=message,
            done_event=done_event,
            **kwargs
        )

    try:
        async with connect(
            host=host,
            port=port,
            configuration=config,
            create_protocol=protocol_factory
        ):
            # Wait until file reception completes or the connection closes
            await done_event

            # If you want to keep the client running even longer,
            # you could do: await asyncio.sleep(60)
            # so you can do more connectivity testing.
            # But the chunked approach + end_stream should be enough.

    except ConnectionRefusedError:
        logging.error("Connection refused. Is the server running on port 4433?")
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QUIC File Client")
    parser.add_argument("--log-level", default="DEBUG", help="DEBUG, INFO, WARNING, etc.")
    parser.add_argument("--file", default="index.html", help="File to request from the server")
    parser.add_argument("--host", default="10.52.2.182", help="Server IP address")
    parser.add_argument("--port", type=int, default=4433, help="Server port")
    args = parser.parse_args()

    asyncio.run(run_client(log_level=args.log_level, filename=args.file, host=args.host, port=args.port))
