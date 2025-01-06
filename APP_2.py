import streamlit as st
from PIL import Image
import pandas as pd
import re
import json
from transformers import DonutProcessor, VisionEncoderDecoderModel
from openpyxl import load_workbook
import os
from datetime import datetime

# LOAD DONUT MODEL & PROCESSOR
@st.cache_resource
def donut_model():
    model_path = "C:/Users/User/Desktop/CORD/MODELCORDv2/ModelDonutCORDv2"
    processor = DonutProcessor.from_pretrained(model_path)
    model = VisionEncoderDecoderModel.from_pretrained(model_path)
    return processor, model

# FUNCTION PARSE RAW OUTPUT
def parse_raw_output(raw_text):
    try:
        # Define a structured output template
        structured_data = {
            "tax_price": "0",
            "service_tax": "0",
            "other_tax": "0",
            "items": [],
            "discount": "0"
        }

        # Pattern to match tax fields
        tax_pattern = r"([\d,]+)\s+([\d,]+)\s+([\d,]+)"

        tax_match = re.search(tax_pattern, raw_text)
        
        if tax_match:
            structured_data["tax_price"] = tax_match.group(1)
            structured_data["service_tax"] = tax_match.group(2)
            structured_data["other_tax"] = tax_match.group(3)
        else:
            st.text("No tax fields found in raw output.")

        # Adjusted regex pattern for items
        item_pattern = r"(\d+)\s+(\d+)\s+(\d+)\s+([\d,]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(.+?)\s+(\d+)"
        
        # Parse items
        for match in re.finditer(item_pattern, raw_text):
            st.text(f"Matched groups: {match.groups()}")  # Debugging regex matches
            item = {
                "unit_price": match.group(4),  # Price
                "sub_unit_price": match.group(5),  # Sub-unit price (if applicable)
                "sub_qty": match.group(6),  # Sub-quantity
                "sub_description": match.group(7),  # Sub-description
                "qty": match.group(8),  # Quantity
                "disc_item": match.group(10),  # Discount on item
                "description": match.group(9)  # Item description
            }
            structured_data["items"].append(item)

        # If no items are detected, add a default entry
        if not structured_data["items"]:
            structured_data["items"].append({
                "unit_price": "0",
                "sub_unit_price": "0",
                "sub_qty": "0",
                "sub_description": "0",
                "qty": "0",
                "disc_item": "0",
                "description": "No items detected",
            })

        return structured_data

    except Exception as e:
        st.error(f"Error parsing raw output: {str(e)}")
        return None

# FUNCTION EXTRACT DATA FROM RECEIPT
def extract_data_from_receipt(image, processor, model):
    try:
        # Process the image into a tensor
        pixel_values = processor(image, return_tensors="pt").pixel_values
        outputs = model.generate(pixel_values, max_length=512)

        # Decode the model output
        predicted_text = processor.batch_decode(outputs, skip_special_tokens=True)[0]
        st.text(f"Raw output from the model: {predicted_text}")  # Debugging raw output

        # Parse the raw text into a structured format
        structured_data = parse_raw_output(predicted_text)
        return structured_data

    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None

# FUNCTION SAVE TO EXCEL WITH PREFIX
def save_to_excel_with_prefix(data, prefix):
    try:
        # Generate a unique file name with a prefix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{prefix}_EXTRACTED_DATA_{timestamp}.xlsx"

        # Prepare "Taxes and Discount" data
        taxes = {
            "Tax Price": data.get("tax_price", "0"),
            "Service Tax": data.get("service_tax", "0"),
            "Other Tax": data.get("other_tax", "0"),
            "Discount": data.get("discount", "0")
        }

        # Prepare "Items" data (flattening items into a single row)
        items = data.get("items", [])
        if items:
            # Flatten item keys with prefixes to avoid column name clashes
            items_flattened = {f"{key}_{i+1}": item[key] for i, item in enumerate(items) for key in item}
        else:
            items_flattened = {}

        # Combine "Taxes and Discount" and "Items" into a single row
        combined_data = {**taxes, **items_flattened}
        combined_df = pd.DataFrame([combined_data])

        with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
            combined_df.to_excel(writer, sheet_name="Extracted Data", index=False)

        st.success(f"Data successfully saved to {file_name}")
    except Exception as e:
        st.error(f"Error saving to Excel: {str(e)}")

# FUNCTION SAVE TO JSON WITH PREFIX
def save_to_json_with_prefix(data, prefix=""):
    try:
        # Generate a unique file name with a prefix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{prefix}_EXTRACTED_DATA_{timestamp}.json" if prefix else f"EXTRACTED_DATA_{timestamp}.json"

        # Write data to a JSON file
        with open(file_name, 'w') as json_file:
            json.dump(data, json_file, indent=4)

        st.success(f"Data successfully saved to {file_name}")
    except Exception as e:
        st.error(f"Error saving to JSON: {str(e)}")

# FUNCTION SAVE TO EXCEL
def save_to_excel(data):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name=f"EXTRACTED_DATA_{timestamp}.xlsx"

        # Prepare "Taxes and Discount" data
        taxes = {
            "Tax Price": data.get("tax_price", "0"),
            "Service Tax": data.get("service_tax", "0"),
            "Other Tax": data.get("other_tax", "0"),
            "Discount": data.get("discount", "0")
        }

        # Prepare "Items" data (flattening items into a single row)
        items = data.get("items", [])
        if items:
            # Flatten item keys with prefixes to avoid column name clashes
            items_flattened = {f"{key}_{i+1}": item[key] for i, item in enumerate(items) for key in item}
        else:
            items_flattened = {}

        # Combine "Taxes and Discount" and "Items" into a single row
        combined_data = {**taxes, **items_flattened}
        combined_df = pd.DataFrame([combined_data])

        # Save to a single Excel sheet
        with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
            combined_df.to_excel(writer, sheet_name="Extracted Data", index=False)

        st.success(f"Data successfully saved to {file_name}")
    except Exception as e:
        st.error(f"Error saving to Excel: {str(e)}")

# FUNCTION SAVE TO JSON
def save_to_json(data):
    try:
        # Generate a unique file name without a prefix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"EXTRACTED_DATA_{timestamp}.json"

        # Write data to a JSON file
        with open(file_name, 'w') as json_file:
            json.dump(data, json_file, indent=4)

        st.success(f"Data successfully saved to {file_name}")
    except Exception as e:
        st.error(f"Error saving to JSON: {str(e)}")

#----------------------------------------------------------------------------------------------------------------------

# STREAMLIT APP
st.markdown("<h1 style='text-align: center; color: #CD5C5C;'>SUB-AIRIS PROJECT</h1>", unsafe_allow_html=True)

# Upload the receipt image
uploaded_file = st.file_uploader("Upload a receipt image", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # Load Donut model and processor
    processor, model = donut_model()

    # Process single image files
    image = Image.open(uploaded_file)

    # Display the uploaded image
    st.image(image, caption="Uploaded Receipt", use_column_width=True)

    # Extract data from the image
    extracted_data = extract_data_from_receipt(image, processor, model)

    # Check if extracted_data is valid
    if extracted_data:
        # Display parsed predictions
        st.markdown('<h2 style="color:#c32148;">RECEIPT\'S OUTPUT:</h2>', unsafe_allow_html=True)
        st.json(extracted_data)
    
        # Display Tax and Discount Data
        taxes = {
            "Tax Price": [extracted_data.get("tax_price", "0")],
            "Service Tax": [extracted_data.get("service_tax", "0")],
            "Other Tax": [extracted_data.get("other_tax", "0")],
            "Discount": [extracted_data.get("discount", "0")]
        }
        taxes_df = pd.DataFrame(taxes)
        st.markdown('<h3 style="color:#b94e48;">TAXES & DISCOUNT :</h3>', unsafe_allow_html=True)
        st.dataframe(taxes_df)

        # Display Items Data
        items = extracted_data.get("items", [])
        if items:
            items_df = pd.DataFrame(items)
            st.markdown('<h4 style="color:#b94e48;">ITEMS :</h4>', unsafe_allow_html=True)
            st.dataframe(items_df)
    else:
        st.error("Error: No valid data extracted from the receipt.")

# Get a custom file name from the user
file_prefix = st.text_input("Enter a custom file name (optional):", "")

if st.button("SAVE TO EXCEL"):
    if file_prefix.strip():
        save_to_excel_with_prefix(extracted_data, file_prefix)
    else:
        save_to_excel(extracted_data)

if st.button("SAVE TO JSON"):
    if file_prefix.strip():
        save_to_json_with_prefix(extracted_data, file_prefix)
    else:
        save_to_json(extracted_data)