from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
import pandas as pd
import requests
import io
import os

app = FastAPI()

# টেমপ্লেট ফোল্ডারের পাথটি নিশ্চিত করার জন্য os.path ব্যবহার করা হলো
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

df_global = None

def load_jee_data():
    global df_global
    github_raw_url = "https://raw.githubusercontent.com/atmabodha/OpenNLP/main/IIT-JEE/JEE_2025_Cutoffs.xlsx"
    try:
        print("GitHub file try to loaded...")
        response = requests.get(github_raw_url)
        df = pd.read_excel(io.BytesIO(response.content), engine='openpyxl')
        
        df['Opening Rank'] = pd.to_numeric(df['Opening Rank'], errors='coerce')
        df['Closing Rank'] = pd.to_numeric(df['Closing Rank'], errors='coerce')
        df = df.dropna(subset=['Opening Rank', 'Closing Rank'])
        
        df_global = df
        print(df.columns.tolist())
        print("🎉 Real Cutoff Data Loaded Successfully into FastAPI!")
    except Exception as e:
        print("Error loading data:", e)

# ডাটা লোড করা শুরু
load_jee_data()

@app.get("/")
def home(request: Request):
    # হোম পেজ লোড করার সময় context-এ অবশ্যই request পাঠাতে হবে
    return templates.TemplateResponse(request=request,
    name="index.html")

@app.post("/predict")
def predict(
    request: Request,
    exam_type: str = Form(...),
    rank: int = Form(...),
    gender: str = Form(...),
    interest: str = Form(None)
):

    print("Selected Exam =", exam_type)
    print("Rank =", rank)
    global df_global
    
    if df_global is None:
        return templates.TemplateResponse("result.html", {"request": request, "error": "Data not loaded yet. Please restart server."})
    
    if gender == "Female":
        gender_filter = "Female-only (including Supernumerary)"
    else:
        gender_filter = "Gender-Neutral"

    if exam_type == "advanced":

        institute_filter = df_global[
             df_global["Institute"].str.contains(
                "Indian Institute of Technology",
               case= False,
               na= False 
             )
        ]    

    else:

        institute_filter = df_global[
             -df_global["Institute"].str.contains(
                "Indian Institute of Technology",
                case=False,
                na=False
             )
        ]
        
    try:

        print("Exam Type =", exam_type)
        print("Total Institutes =",
        len(institute_filter))

        condition = (df_global['Closing Rank'] >= rank) & (df_global['Gender'] == gender_filter)
        filtered_df = institute_filter[condition]
        filtered_df = filtered_df.sort_values(by='Closing Rank').head(20)
        
        colleges_list = []
        for _, row in filtered_df.iterrows():
            colleges_list.append({
                "institute": row['Institute'],
                "program": row['Academic Program Name'],
                "opening": int(row['Opening Rank']),
                "closing": int(row['Closing Rank'])
            })
        
        return templates.TemplateResponse(
            request=request,
            name="result.html", 
            context={
                "rank": rank, 
                "gender": gender,
                "interest": interest,
                "colleges": colleges_list
            }
        )
    except Exception as e:
       print("ERROR:" , e)
       raise e