"""
Ingestion of Company Facts and Submissions bulk data files.

This script parse the bulk json file data into a time ordered sturctured array
which can be represented by a pandas dataframe.

The script handles the following:

1. Loads submissions data files from a specified directory ('data/submissions').
2. Loads companyfacts data files from a specified directory ('data/companyfacts').
3. Passes them to a series of pydantic data models which seperately validates the
    structure of the files and then passes them onto a SECfilling pydantic model
    which selects data of interest and saves it to a jsonl files

### Key Notes:
- The output is a jsonlines file called 'company_facts.jsonl'. Items in the file can
    be easily passed to the 'Stock' class to run the discounted cashflow calculation.
- Is hard coded to only calculate times series on an annualised basis.

Ensure the `data/companyfacts` and `data/submissiosn` directories exist. These can be
downloaded from the sec website: http://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip
"""

import os
import json
import logging
from logging import StreamHandler, FileHandler

from pydantic import ValidationError

from fairvalue.utils import load_json
from fairvalue import ParseException
from fairvalue.models.sec_ingestion import CompanyFacts, Submissions, SECFilings


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def get_logger(
    logger_name: str,
    log_file: str = os.path.join("data", "ingestion_logs.jsonl"),
    level=logging.INFO,
):

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        formatter = JsonFormatter()
        stream_handler = StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        file_handler = FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


logger = get_logger("ingestion")

if __name__ == "__main__":

    DIR = "data"
    COMPANY_FACTS = "companyfacts"
    SUBMISSIONS = "submissions"
    TICKER_DICT_FILENAME = "ticker_mapping.pkl"
    OUTPUT_FILE = "company_facts.jsonl"

    files = os.listdir(os.path.join(DIR, COMPANY_FACTS))

    successful = 0

    for file in files:

        try:
            # loading submissions and companyfacts and passing to SECfillings
            companyfacts_json = load_json(os.path.join(DIR, COMPANY_FACTS, file))
            companyfacts = CompanyFacts(**companyfacts_json)

            submissions_json = load_json(os.path.join(DIR, SUBMISSIONS, file))
            submission = Submissions(**submissions_json)

            sec_filing = SECFilings(companyfacts=companyfacts, submissions=submission)

            logger.info(f"Sucessfully processed file '%s'", file)

            # Pulling the data from the fillings needed to run a cashflow calculation
            financials = sec_filing.to_annual_financials(return_dataframe=True)
            financials_records = financials.to_dict(orient="records")
            for record in financials_records:
                json_line = json.dumps(record)
                with open(os.path.join(DIR, OUTPUT_FILE), "a", encoding="utf-8") as f:
                    f.write(json_line + "\n")

            logger.info(f"Sucessfully processed file '%s'", file)

            successful += 1

        except ParseException as e:
            logger.error("Failed to process file '%s' due to '%s'", file, e)
            continue
        except IndexError as e:
            logger.error("Failed to process file '%s' due to '%s'", file, e)
            continue
        # except KeyError as e:
        #     logger.error("Failed to process file '%s' due to '%s'", file, e)
        #     continue
        except json.JSONDecodeError as e:
            logger.error("Failed to process file '%s' due to '%s'", file, e)
            continue
        except ValidationError as e:
            logger.error("Failed to process file '%s' due to '%s'", file, str(e))
            continue
        except Exception as e:
            new_error_string = f"Failed to process file '{file}' due to {e}"
            logger.error(new_error_string)
            raise type(e)(new_error_string).with_traceback(e.__traceback__)

    logger.info(f"Sucessfully processed  %s/%s files", successful, len(files))
