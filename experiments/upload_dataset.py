import os
import csv
from pathlib import Path

from langfuse import Langfuse

langfuse = Langfuse(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST"),
)


def create_langfuse_dataset(dataset_name):
    langfuse.create_dataset(name=dataset_name)


def insert_langfuse_item(dataset_name, input, expected_output, filename):
    langfuse.create_dataset_item(
        dataset_name=dataset_name,
        # any python object or value, optional
        input=input,
        # any python object or value, optional
        expected_output=expected_output,
        metadata={"filename": filename},
    )


def as_expected_gadm_output(location_name, gadm_id):
    return {"name": location_name, "gadm_id": gadm_id}


def upload_csv(dataset_name, csv_filepath):
    # Calls insert_langfuse_item over a csv
    #
    # Sample CSV:
    #
    # text,id,name,type
    # Show me deforestation trends in Brazil's Amazon rainforest,BRA,Brazil,iso
    # forest fires indonisia last month,IDN,Indonesia,iso
    # Compare logging rates between Peru and Columbia over past 5 years,PER; COL,Peru; Colombia,iso; iso
    #
    # TODO: expected_output is a list of dicts like so:
    # Show me deforestation trends in Brazil's Amazon rainforest,BRA,Brazil,iso
    # [{"name": Brazil, "gadm_id": BRA}]
    # Compare logging rates between Peru and Columbia over past 5 years,PER; COL,Peru; Colombia,iso; iso
    # [{"name": Peru, "gadm_id": PER}, {"name": Colombia, "gadm_id": COL}]

    try:
        with open(csv_filepath, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            csv_filename = Path(csv_filepath).name
            for row in reader:
                input_text = row.get("text")
                gadm_id = row.get("id")
                location_name = row.get("name")
                # The 'type' column is present in the sample CSV but not used here.

                if (
                    input_text is None
                    or gadm_id is None
                    or location_name is None
                ):
                    print(f"Skipping row due to missing data: {row}")
                    continue

                expected_output = as_expected_gadm_output(
                    location_name, gadm_id
                )
                insert_langfuse_item(
                    dataset_name=dataset_name,
                    input=input_text,
                    expected_output=expected_output,
                    filename=csv_filename,
                )
        print(
            f"Successfully uploaded data from {csv_filename} to dataset {dataset_name}"
        )
    except FileNotFoundError:
        print(f"Error: The file {csv_filepath} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
