import logging
import os
from typing import Dict

from waitress import serve as waitress_serve

from siena.core.actions import init_project
from siena.server import create_app
from siena.shared.constants import (
    ServerEnv,
    SIENAConfig,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    ASCII_LOGO,
)
from siena.shared.exceptions.base import (
    SIENABaseException,
)
from siena.shared.exceptions.core import (
    SIENACoreException,
)
from siena.shared.exceptions.server import (
    SIENAServerException,
)

logger = logging.getLogger(__name__)


class SIENAServer:
    def __init__(
            self,
            configs: Dict = None,
            debug_mode: bool = False,
    ):
        self.configs = configs
        self.debug_mode = debug_mode
        self.host = configs[SIENAConfig.SUB_KEY_SERVER_HOST] or DEFAULT_SERVER_HOST
        self.port = configs[SIENAConfig.SUB_KEY_SERVER_PORT] or DEFAULT_SERVER_PORT

        # initialize project
        init_project()

    def run(self) -> None:
        logger.info(f"Starting SIENA server at http://{self.host}:{self.port}")
        try:
            if self.debug_mode:
                logger.warning("Deploying SIENA Server in development mode...")
                os.environ["APP_ENV"] = ServerEnv.DEV
                app = create_app()
                app.run(
                    host=self.host,
                    port=self.port,
                    debug=self.debug_mode
                )
            else:
                logger.info("Deploying SIENA Server in production mode...")
                print(ASCII_LOGO)
                waitress_serve(create_app(), host=self.host, port=self.port)

                # # Run as a shell command if required
                # import subprocess
                # subprocess.run(["waitress-serve", f"--host={self.host}",
                #                 f"--port={self.port}", "siena.server.siena_server:run"])

        except SIENACoreException:
            logger.exception(f"Core Exception")
        except SIENAServerException:
            logger.exception(f"Server Exception")
        except SIENABaseException:
            logger.exception(f"Base Exception")
        except KeyboardInterrupt:
            logger.info(f"Gracefully terminating SIENA Server...")
            exit(1)
        except OSError:
            logger.exception(f"Possible permission exception while starting the SIENA Server")
        except Exception as e:
            logger.exception(f"Base Exception: Broad. more info: {e}")
        return
