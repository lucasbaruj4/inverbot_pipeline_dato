#!/usr/bin/env python
import sys
import warnings

from datetime import datetime
from .data import data_source
from inverbot_pipeline_dato.crew import InverbotPipelineDato

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the crew.
    """
    t = data_source.links()
    try:
        InverbotPipelineDato().crew().kickoff(inputs=t)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")
