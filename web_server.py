import asyncio
import argparse
import logging
import os
import sys

from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived

from log_config import setup_logging


class FileServerProtocol(QuicConnectionProtocol):
    """
    A simple file-serving QUIC protocol:
      - Expects each stream's data to be a filename (UTF-8).
      - Reads that file from the configured directory (self.directory).
      - Returns the file contents over the same stream.
    """
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.directory = directory

    def quic_event_received(self, event):
        # For debug logging, see what's happening
        logging.debug(f"Server received event: {event}")

        if isinstance(event, StreamDataReceived):
            stream_id = event.stream_id
            data = event.data  # bytes
            logging.info(f"Received request on stream {stream_id}: {data!r}")

            # Convert the received bytes to a path string
            filename = data.decode(errors="replace").strip()
            
            # Build full path: be careful to avoid directory traversal in real code!
            requested_path = os.path.join(self.directory, filename)

            # Attempt to read the file
            try:
                # Optionally sanitize the path to ensure it's inside self.directory
                normalized_path = os.path.normpath(requested_path)
                if not normalized_path.startswith(os.path.abspath(self.directory)):
                    raise FileNotFoundError("Attempted directory traversal")

                with open(normalized_path, "rb") as f:
                    file_contents = f.read()

                logging.info(f"Serving file: {normalized_path} ({len(file_contents)} bytes)")
                self._quic.send_stream_data(stream_id, file_contents, end_stream=True)

            except FileNotFoundError:
                error_msg = f"File not found: {filename}"
                logging.warning(error_msg)
                self._quic.send_stream_data(stream_id, error_msg.encode(), end_stream=True)
            except IsADirectoryError:
                error_msg = f"Requested path is a directory: {filename}"
                logging.warning(error_msg)
                self._quic.send_stream_data(stream_id, error_msg.encode(), end_stream=True)
            except Exception as exc:
                error_msg = f"Error reading file '{filename}': {exc}"
                logging.error(error_msg)
                self._quic.send_stream_data(stream_id, error_msg.encode(), end_stream=True)


async def main():
    parser = argparse.ArgumentParser(description="QUIC File Server")
    parser.add_argument("--cert", type=str, default="keys/cert.pem", help="Path to certificate file")
    parser.add_argument("--key", type=str, default="keys/key.pem", help="Path to private key file")
    parser.add_argument("--log-level", type=str, default="DEBUG", help="Set log level (DEBUG, INFO, WARNING)")
    parser.add_argument("--directory", type=str, default="public", help="Folder to serve files from")
    args = parser.parse_args()

    setup_logging(log_file="web_server.log", level=args.log_level)

    # Validate directory
    directory = os.path.abspath(args.directory)
    if not os.path.isdir(directory):
        print(f"Error: --directory is not a valid folder: {directory}")
        sys.exit(1)

    configuration = QuicConfiguration(is_client=False)
    try:
        configuration.load_cert_chain(certfile=args.cert, keyfile=args.key)
    except Exception as e:
        logging.error(f"Failed to load certificate/key: {e}")
        sys.exit(1)

    try:
        logging.info(f"Starting QUIC server on 0.0.0.0:4433, serving files from {directory} ...")
        
        # Provide a protocol factory that includes the directory argument
        def protocol_factory(*proto_args, **proto_kwargs):
            return FileServerProtocol(*proto_args, directory=directory, **proto_kwargs)

        server = await serve(
            host="0.0.0.0",
            port=4433,
            configuration=configuration,
            create_protocol=protocol_factory,
        )

        # Keep the server alive indefinitely (until Ctrl+C)
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
