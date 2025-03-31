import asyncio
import argparse
import logging
import sys

from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived

from log_config import setup_logging

class EchoServerProtocol(QuicConnectionProtocol):
    def quic_event_received(self, event):
        logging.debug(f"Server received event: {event}")
        if isinstance(event, StreamDataReceived):
            stream_id = event.stream_id
            data = event.data
            logging.info(f"Received on stream {stream_id}: {data.decode()}")
            self._quic.send_stream_data(stream_id, data, end_stream=True)

async def main():
    parser = argparse.ArgumentParser(description="QUIC Echo Server")
    parser.add_argument("--cert", type=str, default="keys/cert.pem", help="Path to certificate file")
    parser.add_argument("--key", type=str, default="keys/key.pem", help="Path to private key file")
    parser.add_argument("--log-level", type=str, default="DEBUG", help="Set log level (DEBUG, INFO, WARNING)")
    args = parser.parse_args()

    setup_logging(log_file="echo_server.log", level=args.log_level)

    configuration = QuicConfiguration(is_client=False)
    try:
        configuration.load_cert_chain(certfile=args.cert, keyfile=args.key)
    except Exception as e:
        logging.error(f"Failed to load certificate/key: {e}")
        sys.exit(1)

    try:
        logging.info("Starting QUIC server on 0.0.0.0:4433...")
        
        # Await the serve() call (no "async with"), then block indefinitely.
        server = await serve(
            host="0.0.0.0",
            port=4433,
            configuration=configuration,
            create_protocol=EchoServerProtocol,
        )

        # Keep the server alive indefinitely. (Press Ctrl+C to stop.)
        await asyncio.Future()

    except OSError as e:
        logging.error(f"Failed to start server: {e}")
        logging.debug("This could be due to the port already being in use.")
        sys.exit(1)
    except Exception as e:
        logging.exception(f"Unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
