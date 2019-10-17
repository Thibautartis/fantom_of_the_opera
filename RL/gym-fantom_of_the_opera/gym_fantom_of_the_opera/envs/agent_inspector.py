import socket
import os
import logging
from logging.handlers import RotatingFileHandler
import protocol
from random import randrange
import random
import time
import sys

import game_globals

# host = "localhost"
# # port = 12000
# port = int(sys.argv[1])
# # HEADERSIZE = 10

class PlayerInspector():

    def __init__(self, nb_session):

        self.end = False

        self.win = 0

        self.nb_session = nb_session
        # self.old_question = ""
        # self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        """
        set up inspector logging
        """
        self.inspector_logger = logging.getLogger()
        self.inspector_logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s :: %(levelname)s :: %(message)s", "%H:%M:%S")
        filename = "./logs/inspector" + str(self.nb_session) + ".log"
        # file
        if os.path.exists(filename):
            os.remove(filename)
        file_handler = RotatingFileHandler(filename, 'a', 1000000, 1)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.inspector_logger.addHandler(file_handler)
        # stream
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.WARNING)
        self.inspector_logger.addHandler(stream_handler)


    # def connect(self):
    #     self.socket.connect((host, port))

    # def reset(self):
    #     self.socket.close()

    def answer(self, question):
        # work
        data = question["data"]
        game_state = question["game state"]
        response_index = random.randint(0, len(data)-1)
        # log
        self.inspector_logger.debug("|\n|")
        self.inspector_logger.debug("inspector answers")
        self.inspector_logger.debug(f"question type ----- {question['question type']}")
        self.inspector_logger.debug(f"data -------------- {data}")
        self.inspector_logger.debug(f"response index ---- {response_index}")
        self.inspector_logger.debug(f"response ---------- {data[response_index]}")
        return response_index

    #*********************************************************************************#
    # Reward management

    def set_win(self, res):
        if res:
            self.win = 50
            print("\n\nINSPECTOR : IVE WON\n\n")
        else:
            self.win = -50


    def set_values_for_reward(self, game_state):
        nbs = 0
        for char in game_state["characters"]:
            if char["suspect"]:
                nbs += 1
        game_globals.gold_position_carlotta = game_globals.gposition_carlotta
        game_globals.gold_nb_suspects = game_globals.gnb_suspects
        game_globals.gposition_carlotta = game_state["position_carlotta"]
        game_globals.nb_suspects = nbs
        game_globals.gold_game_state = game_globals.ggame_state
        game_globals.ggame_state = game_state


    def evaluate_reward(self):
        carlotta_reward = (game_globals.gold_position_carlotta - game_globals.gposition_carlotta)
        suspects_reward = (game_globals.gold_nb_suspects - game_globals.gnb_suspects) * 3

        return (carlotta_reward + suspects_reward + self.win) * 10

    #*********************************************************************************#
