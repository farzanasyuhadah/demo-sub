import streamlit as st
import pandas as pd
import re
import json
import os
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from datetime import datetime

# LOAD DONUT MODEL & PROCESSOR
@st.cache_resource
def donut_model():
    with st.spinner("Loading Donut model and processor..."):
        model_path = "Faz1306/donut-cord-SavedModelv2"
        processor = DonutProcessor.from_pretrained(model_path)
        model = VisionEncoderDecoderModel.from_pretrained(model_path)
    return processor, model

# FUNCTION TO SAFELY CONVERT TO FLOAT
def safe_float(value):
    try:
        if isinstance(value, str):
            cleaned_value = value.replace(',', '').strip()
            return float(cleaned_value)
        return float(value)
    except (ValueError, AttributeError):
        st.error(f"Error: Cannot convert {value} to float.")
        return 0.0

# FUNCTION TO PARSE RAW OUTPUT
def parse_raw_output(raw_text):
    try:
        structured_data = {
            "tax_price": 0.0,
            "service_tax": 0.0,
            "other_tax": 0.0,
            "items": [],
            "discount": 0.0
        }

        # Pattern to extract tax fields
        tax_pattern = r"([\d,]+)\s+([\d,]+)\s+([\d,]+)"
        tax_match = re.search(tax_pattern, raw_text)
        if tax_match:
            structured_data["tax_price"] = safe_float(tax_match.group(1))
            structured_data["service_tax"] = safe_float(tax_match.group(2))
            structured_data["other_tax"] = safe_float(tax_match.group(3))
        else:
            st.warning("Warning: No tax fields found in raw output.")

        # Pattern to match item details
        item_pattern = r"(\d+)\s+(\d+)\s+(\d+)\s+([\d,]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(.+?)\s+(\d+)"
        for match in re.finditer(item_pattern, raw_text):
            item = {
                "unit_price": safe_float(match.group(4)),
                "sub_unit_price": safe_float(match.group(5)),
                "sub_qty": safe_float(match.group(6)),
                "sub_description": match.group(7),
                "qty": safe_float(match.group(8)),
                "disc_item": safe_float(match.group(10)),
                "description": match.group(9)
            }
            structured_data["items"].append(item)

        if not structured_data["items"]:
            structured_data["items"].append({
                "unit_price": 0.0,
                "sub_unit_price": 0.0,
                "sub_qty": 0.0,
                "sub_description": "No sub-details available.",
                "qty": 0.0,
                "disc_item": 0.0,
                "description": "No items detected."
            })

        return structured_data
    except Exception as e:
        st.error(f"Error parsing raw output: {str(e)}")
        return None

# FUNCTION TO EXTRACT DATA FROM RECEIPT
def extract_data_from_receipt(image, processor, model):
    try:
        pixel_values = processor(image, return_tensors="pt").pixel_values
        outputs = model.generate(pixel_values, max_length=512)
        predicted_text = processor.batch_decode(outputs, skip_special_tokens=True)[0]
        st.text(f"Raw output from the model: {predicted_text}")
        return parse_raw_output(predicted_text)
    except Exception as e:
        st.error(f"Unexpected error during extraction: {str(e)}")
        return None

# FUNCTION TO SAVE DATA TO EXCEL TEMPLATE
def save_to_excel_template(data):
    try:
        excel_file = "C:/Users/User/Desktop/AMIC-HRA-F-008 PR (2).xlsx"
        wb = load_workbook(excel_file)
        sheet = wb.active

        # Map JSON keys to Excel columns
        start_row = 13
        col_map = {
            "B": "description",
            "Q": "unit_price",
            "T": "qty",
            "V": "disc_item",
        }

        current_row = start_row
        for item in data["items"]:
            for col, json_key in col_map.items():
                cell = sheet[f"{col}{current_row}"]
                cell.value = item.get(json_key, "")

            if item.get("sub_description") or item.get("sub_unit_price") or item.get("sub_qty"):
                current_row += 1
                sheet[f"B{current_row}"].value = item.get("sub_description", "")
                sheet[f"Q{current_row}"].value = item.get("sub_unit_price", "")
                sheet[f"T{current_row}"].value = item.get("sub_qty", "")

            current_row += 1

        tax_cell = "Y54"
        total_tax = data.get("tax_price", 0.0) + data.get("service_tax", 0.0) + data.get("other_tax", 0.0)
        sheet[tax_cell] = total_tax

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"C:/Users/User/Desktop/PR_TEMPLATE_{timestamp}.xlsx"
        wb.save(output_file)
        st.success(f"Updated Excel file saved at: {output_file}")
    except Exception as e:
        st.error(f"Error saving to Excel: {str(e)}")

# STREAMLIT APP
st.markdown("<h1 style='text-align: center; color: #CD5C5C;'>AIRIS PROJECT</h1>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload a receipt image", type=["jpg", "png", "jpeg"])

if uploaded_file:
    processor, model = donut_model()
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Receipt", use_column_width=True)

    with st.spinner("Processing the model and data extraction.... Please Wait!"):
        extracted_data = extract_data_from_receipt(image, processor, model)

    if extracted_data:
        st.markdown('<h2 style="color:#c32148;">RECEIPT\'S OUTPUT:</h2>', unsafe_allow_html=True)
        st.json(extracted_data)

        taxes = {
            "Tax Price": [extracted_data.get("tax_price", 0.0)],
            "Service Tax": [extracted_data.get("service_tax", 0.0)],
            "Other Tax": [extracted_data.get("other_tax", 0.0)],
            "Total Tax": [
                extracted_data.get("tax_price", 0.0) +
                extracted_data.get("service_tax", 0.0) +
                extracted_data.get("other_tax", 0.0)
            ]
        }
        taxes_df = pd.DataFrame(taxes)
        st.dataframe(taxes_df)

        items_data = []
        for item in extracted_data["items"]:
            items_data.append({
                "Description": item.get("description", ""),
                "Unit Price": item.get("unit_price", ""),
                "Quantity": item.get("qty", ""),
                "Discount": item.get("disc_item", "")
            })

            if item.get("sub_description"):
                items_data.append({
                    "Description": item.get("sub_description", ""),
                    "Unit Price": item.get("sub_unit_price", ""),
                    "Quantity": item.get("sub_qty", ""),
                    "Discount": ""
                })

        st.dataframe(pd.DataFrame(items_data))

    if st.button("SAVE TO EXCEL"):
        save_to_excel_template(extracted_data)
