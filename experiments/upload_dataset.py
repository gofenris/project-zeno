import os

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
    pass
