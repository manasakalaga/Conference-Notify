import logging
import json
import argparse
import importlib
import traceback
import os
from utility import str2bool , get_logger , print_start , LOG_STREAM_OPTIONS , LOG_LEVEL_OPTIONS
from process import MultiProcessingContext


##
#
# Test whether the initialization is working or not
# >> python app.py -l debug -ls console  --test True
#
# Test whether the run is working or not
# >> python app.py -l debug -ls file --test False
#
#

parser = argparse.ArgumentParser()
parser.add_argument(
    "-c",
    "--config",
    default="config.json",
    type=str,
    action="store",
    dest="config",
    help="Specify config.json file",
)
parser.add_argument(
    "-l",
    "--log",
    default="debug",
    action="store",
    dest="log_level",
    choices= LOG_LEVEL_OPTIONS,
    help="Specify the debug level ,default: %(default)s",
)
parser.add_argument(
    "-t",
    "--test",
    default=True,
    type=str2bool,
    action="store",
    dest="test",
    help="Specify whether to test app initialization or run the scrappers ,default: %(default)s",
)
parser.add_argument(
    "-ls",
    "--logStream",
    default="console",
    type=str,
    action="store",
    dest="log_stream",
    choices= LOG_STREAM_OPTIONS,
    help="Specify whether to print logs on terminal or to file ,default: %(default)s",
)
values = parser.parse_args()

log_level = values.log_level.lower()
log_stream = values.log_stream.lower()

if log_level not in LOG_LEVEL_OPTIONS:
    raise ValueError(
        "Unsupported log level. Supported levels: debug , warn , info , error"
    )
if log_stream not in LOG_STREAM_OPTIONS:
    raise ValueError("Unsupported log stream. Supported levels: file , console")


is_test = values.test

CONFIG = values.config



def parse_dbconfig(configuration):
    db_configuration = configuration["database"]
    path = db_configuration["plugin"]["filename"]
    classname = db_configuration["plugin"]["class"]
    module = importlib.import_module(path, ".")
    Database = module.__getattribute__(classname)
    return Database , db_configuration


if __name__ == "__main__":

    with open(CONFIG) as file:
        configuration = json.load(file)
    
    Database_module  , db_configuration = parse_dbconfig(configuration)

    ## reading logging configuration
    logging_configuration = configuration["logging"]
    log_folder = logging_configuration["output"]
    
    if not log_folder in os.listdir('.'):
        os.mkdir(log_folder)

    logger = get_logger(__name__, log_level, log_stream , log_folder)
    ## logger for main thread

    ## logger test in main thread
    print_start(logger)
    logger.info("Application started , Extracting all the plugins")


    ## handles creating mutiple process 
    ## from single process using MultiProcessing  
    

    import_list = configuration["plugins"]
    
    with MultiProcessingContext( log_level , log_stream , log_folder) as execute:
        
        for attr in import_list:
            path = attr["filename"]
            class_name = attr["class"]
            plugin_module = importlib.import_module(path, ".")
            scrapper = plugin_module.__getattribute__(class_name)

            try:
                
                if is_test:
                    scrapper(   log_level = log_level, 
                                log_stream = log_stream ,
                                log_folder = log_folder, 
                                database_module = Database_module, 
                                db_configuration = db_configuration
                            )
                else:
                    execute(    scrapper  , log_level = log_level, 
                                            log_stream = log_stream ,
                                            log_folder = log_folder,
                                            database_module = Database_module, 
                                            db_configuration = db_configuration
                                            )
                                            
            except Exception as e:
                logger.error("{} execute failed for".format(class_name))
                traceback.print_exception(type(e), e, e.__traceback__)
    logger.info("Scrapping done from all Scrapper plugins")
