import json
import logging
import os.path
import subprocess
import sys
import threading
import time
import rosservice
from threading import Thread

from psutil import NoSuchProcess

from src.libs.applications.compatibility.client import Client
from src.libs.process_utils import stop_process_and_children
from src.manager.application.robotics_python_application_interface import IRoboticsPythonApplication
from src.manager.lint.linter import Lint
from src.ram_logging.log_manager import LogManager

logger = LogManager.getLogger(__name__)


class CompatibilityExerciseWrapper(IRoboticsPythonApplication):
    def __init__(self, exercise_command, gui_command, update_callback):
        super().__init__(update_callback)

        home_dir = os.path.expanduser('~')
        self.running = False
        self.linter = Lint()
        # TODO: review hardcoded values
        process_ready, self.exercise_server = self._run_exercise_server(f"python {exercise_command}",
                                                                        f'{home_dir}/ws_code.log',
                                                                        'websocket_code=ready')
        if process_ready:
            logger.info(f"Exercise code {exercise_command} launched")
            time.sleep(1)
            self.exercise_connection = Client('ws://127.0.0.1:1905', 'exercise', self.server_message)
            self.exercise_connection.start()
        else:
            self.exercise_server.kill()
            raise RuntimeError(f"Exercise {exercise_command} could not be run")

        process_ready, self.gui_server = self._run_exercise_server(f"python {gui_command}", f'{home_dir}/ws_gui.log',
                                                                   'websocket_gui=ready')
        if process_ready:
            logger.info(f"Exercise gui {gui_command} launched")
            time.sleep(1)
            self.gui_connection = Client('ws://127.0.0.1:2303', 'gui', self.server_message)
            self.gui_connection.start()
        else:
            self.gui_server.kill()
            raise RuntimeError(f"Exercise GUI {gui_command} could not be run")

        self.pause()
        self.running = True

    def _run_exercise_server(self, cmd, log_file, load_string, timeout: int = 5):
        process = subprocess.Popen(f"{cmd}", shell=True, stdout=None, stderr=subprocess.STDOUT, bufsize=1024,
                                   universal_newlines=True)

        process_ready = False
        while not process_ready:
            try:
                f = open(log_file, "r")
                if f.readline() == load_string:
                    process_ready = True
                f.close()
                time.sleep(0.2)
            except Exception as e:
                logger.debug(f"waiting for server string '{load_string}'...")
                time.sleep(0.2)

        return process_ready, process

    def server_message(self, name, message):
        if name == "gui":  # message received from GUI server
            logger.debug(f"Message received from gui: {message[:30]}")
            self._process_gui_message(message)
        elif name == "exercise":  # message received from EXERCISE server
            logger.info(f"Message received from exercise: {message[:30]}")
            self._process_exercise_message(message)

    def _process_gui_message(self, message):
        if message[0] == "#":
            payload = json.loads(message[4:])
            self.update_callback(payload)
            self.gui_connection.send("#ack")
        else:
            logger.info(f"Message from gui [{message}] is not a valid message")

    def _process_exercise_message(self, message):
        if message[0] == "#":
            payload = json.loads(message[5:])
            self.update_callback(payload)
            self.exercise_connection.send("#ack")
        else:
            logger.info(f"Message from exercise [{message}] is not a valid message")

    def run(self):
        def send_freq():
            while self.is_alive:
                if self.exercise_connection.is_alive():
                    self.exercise_connection.send('#freq{"brain": 20, "gui": 10, "rtf": 100}')
                time.sleep(1)

        rosservice.call_service("/gazebo/unpause_physics", [])
        daemon = Thread(target=send_freq, daemon=False, name='Monitor frequencies')
        daemon.start()

    def stop(self):
        rosservice.call_service('/gazebo/pause_physics', [])
        rosservice.call_service("/gazebo/reset_world", [])

    def resume(self):
        rosservice.call_service("/gazebo/unpause_physics", [])

    def pause(self):
        rosservice.call_service('/gazebo/pause_physics', [])

    def restart(self):
        pass

    @property
    def is_alive(self):
        return self.running

    def load_code(self, code: str):
        errors = self.linter.evaluate_code(code)
        if errors == "":
            self.exercise_connection.send(f"#code {code}")
        else:
            raise Exception(errors)

    def terminate(self):
        self.gui_connection.stop()
        self.exercise_connection.stop()

        try:
            stop_process_and_children(self.gui_server)
        except NoSuchProcess as ex:
            logger.error(f"Wanted to stop GUI server (pid {self.gui_server.pid}) but it's not running")

        try:
            stop_process_and_children(self.exercise_server)
        except NoSuchProcess:
            logger.error(f"Wanted to stop EXERCISE server (pid {self.exercise_server.pid}) but it's not running")

        self.running = False
