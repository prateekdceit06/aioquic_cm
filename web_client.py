import argparse
import asyncio
import logging
from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived

from log_config import setup_logging


class EchoClientProtocol(QuicConnectionProtocol):
    """
    Subclass QuicConnectionProtocol so we can:
      1. open a stream,
      2. send data (in this case, a file name),
      3. receive the response in quic_event_received(),
      4. signal the main code when we're done.
    """
    def __init__(self, *args, message: bytes, done_event: asyncio.Future, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message
        self.done_event = done_event
        self.stream_id = None

    def connection_made(self, transport):
        """Called when the connection is established."""
        super().connection_made(transport)

        # Get a new bidirectional stream ID, and send our data
        self.stream_id = self._quic.get_next_available_stream_id()
        self._quic.send_stream_data(self.stream_id, self.message, end_stream=True)
        logging.info(f"Sending file request: {self.message.decode()}")

    def quic_event_received(self, event):
        """Called whenever a QUIC event occurs."""
        if isinstance(event, StreamDataReceived):
            # If it's the response for our stream_id, log it and signal we're done
            if event.stream_id == self.stream_id:
                response_text = event.data.decode(errors="replace")
                logging.info(f"Received response:\n{response_text}")
                # Let main() know we got our response
                if not self.done_event.done():
                    self.done_event.set_result(True)


async def run_client(log_level, filename, host, port):
    setup_logging(log_file="web_client.log", level=log_level)

    config = QuicConfiguration(is_client=True)
    # Disable cert verification for testing with self-signed cert
    config.verify_mode = False
    # Must match your certificate’s common name (CN) or subjectAltName
    config.server_name = host
    config.port = port

    # We'll signal this future once the response is received
    done_event = asyncio.get_event_loop().create_future()

    # Prepare the bytes message (file name)
    message = filename.encode()

    # Build our custom protocol factory, passing the message + done_event
    def protocol_factory(*args, **kwargs):
        return EchoClientProtocol(
            *args,
            message=message,
            done_event=done_event,
            **kwargs
        )

    try:
        async with connect(
            host, port,
            configuration=config,
            create_protocol=protocol_factory
        ) as client:
            # Wait until we get the response or the connection closes
            await done_event
    except ConnectionRefusedError:
        logging.error("Connection refused. Is the server running on localhost:4433?")
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QUIC Client")
    parser.add_argument("--log-level", default="DEBUG", help="DEBUG, INFO, WARNING, etc.")
    parser.add_argument("--file", default="index.html", help="File to request from the server")
    parser.add_argument("--host", default="10.52.2.182", help="Server IP address")
    parser.add_argument("--port", default="4433", help="Server port")
    args = parser.parse_args()

    asyncio.run(run_client(log_level=args.log_level, filename=args.file, host=args.host, port=args.port))
