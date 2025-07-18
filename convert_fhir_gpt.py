import re
import uuid
from fhir.resources import bundle, patient, observation, identifier, narrative, humanname, codeableconcept, coding # <TODO>, <TODO>, <TODO>
from datetime import datetime, timedelta
import pandas as pd

loinc_codes = {
    'Pregnancy': ('82810-3', 'Pregnancy', 'mg/dL', 'Laboratory', 'laboratory'), #1 DONE TODO-FHIR What's my status? I am or I am I not?
    'Glucose': ('15074-8', 'Glucose [Moles/volume] in Blood', 'mg/dL','Laboratory', 'laboratory'),
    'BloodPressure': ('85354-9', 'Blood pressure panel with all children optional', 'mm[Hg]', "Vital Signs", "vital-signs"),
    'Insulin': ('14749-6','Glucose [Moles/volume] in Serum or Plasma', 'mg/dL','Laboratory', 'laboratory'),
    'BMI': ('39156-5', 'BMI', 'kg/m3', "Vital Signs", "vital-signs"),  #2 DONE TODO-FHIR I am slim on a completely different power
}

# Example billable dollars for each observation
billable_dollars = {
    'Pregnancy': 50.0,
    'Glucose': 75.0,
    'BloodPressure': 100.0,
    'Insulin': 80.0,
    'BMI': 90.0,
}

def calculate_bd(age):
    """ This calculates the birthyear of a patient """
    year = (datetime.now() - timedelta(days=age)).year  #TODO So many days to get it right!
    return f"{year}-1-1"

def convert_table_to_fhir_bundle(index, row):
    pid = str(uuid4())
    oid = str(uuid.uuid4())
    peid = str(uuid.uuid4())

    fhir_bundle = bundle.Bundle(resourceType = 'Bundle', type = 'collection', entry = [])
    # Create Observation resources for each column in the table
    columns = row.keys()

    # Creating a unique identifier for the patient
    patient_identifier = identifier.Identifier()
    patient_identifier.system = 'fohispital.thd/patient-ids' #3 TODO-FHIR I am into etiquette now, protocols are for losers.
    patient_identifier.value = str(index)

    # Create a Patient resource for each record
    patient_resource = patient.Patient(
        id = f'Patient-{pid',
        birthDate = calculate_bd(row['Age']),
        identifier = [patient_identifier],
        text=narrative.Narrative(
            status="generated",
            div="<div xmlns='http://www.w3.org/1999/xhtml'>A patient resource with a narrative.</div>",
        )
    )

    # Append Entry to Bundle
    fhir_bundle.entry.append(
        bundle.BundleEntry(
            resource = patient_resource,
            fullUrl = f'http://fohispital.thd/{patient_resource.id}'
        )
    )

    # Create Observation resources for each column except the first (assuming the first column is an identifier)
    # TODO: Below are two objects that are named incorrectly, they need to replaced with actual objectsnames from fhir.resources
    # Check the imports up top to find out which. I am curious, if you can handle this observation.
    for i, column in enumerate(columns):
        if column in ['Age', 'Outcome']:
            continue

        observation_resource = observation.Observation(
            id = f"observation-{index}-{oid}-{}", #4 TODO You are all different - No, I am not!
            status = 'final',
            category = [observation.CodeableConcept(
                coding=[observation.Coding(system='http://terminology.hl7.org/CodeSystem/observation-category', code=loinc_codes[column][4], display=loinc_codes[column][3])]
                )],
            code = codeableconcept.CodeableConcept(
                coding=[coding.Coding(system='http://loinc.org', code=loinc_codes[column][0], display=loinc_codes[column][1])]
                ),
            subject = reference.Reference(reference=f'Patient/{index}'),
            performer=[reference.Reference(reference=f"Practitioner/{peid}")],
            text=narrative.Narrative(
                status="generated",
                div="<div xmlns='http://www.w3.org/1999/xhtml'>An observation resource with a narrative.</div>",
                ),
            effectiveDateTime = f"{datetime.utcnow().isoformat()}" #5 TODO A wrong watch is right at least twice a day.
        )

        if column == "BloodPressure":
            observation_resource.component = [
                observation.ObservationComponent(
                    code=codeableconcept.CodeableConcept(
                        coding=[
                            coding.Coding(
                                system="http://loinc.org", code="8480-6", display="Systolic Blood Pressure"
                            )
                        ]
                    ),
                    valueQuantity=quantity.Quantity(
                        value=row[column]+40, # DISCLAIMER: Let's not have a cardiologist see this - IGNORE FOR THE EXAM :-)
                        unit="mmHg",
                        system="http://unitsofmeasure.org",
                        code="mm[Hg]",
                    ),
                ),
                observation.ObservationComponent(
                    code=codeableconcept.CodeableConcept(
                        coding=[
                            coding.Coding(
                                system="http://loinc.org", code="8462-4", display="Diastolic Blood Pressure"
                            )
                        ]
                    ),
                    valueQuantity=quantity.Quantity(
                        value=row[column],
                        unit="mmHg",
                        system="http://unitsofmeasure.org",
                        code="mm[Hg]",
                    ),
                )
        ]
        else:
            observation_resource.valueQuantity = quantity.Quantity(
                    value=row[column],
                    unit=loinc_codes[column][2],
                    system="http://unitsofmeasure.org",
                    code=loinc_codes[column][2],
                )

        fhir_bundle.entry.append(
            bundle.BundleEntry(
                resource = observation_resource,
                fullUrl = f'http://fohispital.thd/{observation_resource.id}'
            )
        )

    return fhir_bundle

# Test-Example usage with a pandas DataFrame
df = pd.DataFrame({
    'Pregnancy': [6, 7],
    'Glucose': [148, 120],
    'BloodPressure': [72, 80],
    'Insulin': [0, 30],
    'BMI': [33.6, 25.4],
    'Age': [50, 35],
})

# Uncomment to check final code
# df = pd.read_csv('diabetes_clean.csv')

for index, row in df.iterrows():
    with open(f"{index}.json", 'w') as file:
        fhir_bundle = convert_table_to_fhir_bundle(index,row)
        print(fhir_bundle.json(indent=2))
        file.write(fhir_bundle.json(index=2))


