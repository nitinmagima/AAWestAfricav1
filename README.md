

### **AA West Africa - Rainfall Hindcast Interactive Dashboard**  

This **Streamlit web app** allows users to **analyze and compare hindcast rainfall data** across multiple regions, countries, and seasons. Users can:
- **Select multiple regions** for comparison.
- **Set a rainfall threshold** to detect bad years.
- **Visualize rainfall trends** with interactive charts.
- **Download detected bad years** as a CSV file.

---

### **Features**  
✅ **Multi-Region Comparison** – Compare multiple locations on one graph.  
✅ **Hindcast Rainfall Threshold Slider** – Identify years with low rainfall.  
✅ **Interactive Plotly Charts** – Zoom, pan, and hover for details.  
✅ **Formatted Bad Years Table** – Years below the threshold are marked.  
✅ **Frequency-Based Bad Year Selection** – Sorts rainfall values and allows users to select the lowest X% of years.
✅ **CSV Download Option** – Export bad years for further analysis.  

---

### Installation**  
Make sure you have **Python 3.x** installed. Then, install the required libraries:  

```bash
pip install streamlit pandas plotly
```

---

### **▶️ Run the App**  
Run the Streamlit app using:  

```bash
streamlit run Single_Season_Rainfall_Hindcast_Analysis.py
```

---

### **📂 Folder Structure**  

```
📂 data/
 ├── 📂 Country1/
 │   ├── 📂 Season1/
 │   │   ├── Region1.csv
 │   │   ├── Region2.csv
 │   │   ├── ...
 │   ├── 📂 Season2/
 ├── 📂 Country2/
```
- **Countries** contain **seasons**, which contain **CSV files** with rainfall data.

---

### **📊 Data Format** (CSV Files)  
Each CSV file should contain **two columns** without headers:  

| Year (Index) | Rainfall (mm) |  
|--------------|--------------|  
| 1            | 102.4        |  
| 2            | 98.7         |  
| ...          | ...          |  


- **The first column (Year Index) maps to real years** (1 → 1991, 35 → 2025).  
- **The second column contains rainfall values in mm.**  

---

### **📝 Notes**  
- The **first column is converted to real years** (e.g., `1 → 1991`).
- The **"Bad Years" table marks years below the selected threshold**.

---


