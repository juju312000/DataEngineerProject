from pymongo import MongoClient
import time
import pandas as pd
import json
import plotly
import plotly.express as px
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.arima.model import ARIMA
from flask import Flask, render_template, redirect, url_for, request

# Init Flask server
app = Flask(__name__, template_folder='./templates')

# Main Page redirect immediately on bitcoin graphics page
@app.route("/")
def home():
    return redirect(url_for('graphCrypto', crypto="bitcoin", cryptoname="bitcoin"))

# Graph page show 3 graphics "("open", "marketcap", "volume")" by using plotly express package
# In case of GET method show 3 graphics
# In case of POST methode change the <crypto> show on graph by reload this page with an other url
@app.route("/graph/<crypto>", methods=['GET', 'POST'])
def graphCrypto(crypto):
    if request.method == 'GET':
        # Get the data of "crypto" in mongo db collection
        df = pd.DataFrame(list(db[str(crypto)].find()))[["date", "marketcap", "volume", "open"]]

        # Create the 3 graphics
        graph = []
        for i in ("open", "marketcap", "volume"):
            fig = px.line(df, x='date', y=i, title=i + " value of " + crypto)
            fig.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)', 'paper_bgcolor': 'rgba(0, 0, 0, 0)'},
                              title_font_color='#E6B11B', legend_font_color="White", title_x=0.5)
            fig.update_traces(line_color='#E6B11B')
            fig.update_yaxes(showgrid=False, color="White")
            fig.update_xaxes(showgrid=False, color="White")
            graph.append(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))

        # return the 3 graphs on the HTML template
        return render_template('template_home.html', graphJSON=graph[0], graphJSON2=graph[1],
                               graphJSON3=graph[2], data=db.list_collection_names())

    elif request.method == 'POST':
        data = request.form.get("comp_select")
        return redirect(url_for('graphCrypto', crypto=data ))

# Predict page build prediction and show them
@app.route("/graph/<crypto>/predict", methods=['GET', 'POST'])
def predict(crypto):
    if request.method == 'GET':
        # Get the IA graph in json model
        graphJSON = IA(str(crypto))
        return render_template('template_predict.html', graphJSON=graphJSON, data=db.list_collection_names())

    elif request.method == 'POST':
        data = request.form.get("comp_select")
        return redirect(url_for('predict', crypto=data))

# Build the prediction by using SAMIRAX and AMIRA model
def IA(crypto):
    df = pd.DataFrame(list(db[crypto].find()))[["date", "marketcap", "volume", "open"]]
    df = df.iloc[::-1].reset_index()
    df["date"] = pd.to_datetime(df["date"], format='%Y-%m-%d')

    # Define a size for the train/test sets
    train_size = int(0.8 * len(df))
    train_set = df[:train_size]
    test_set = df[train_size:]

    y_train = train_set['open']
    y_test = test_set['open']

    df["train"] = y_train
    df["test"] = y_test

    # First model SAMIRAX
    ARMAmodel = SARIMAX(y_train, order=(3, 2, 3))
    ARMAmodel = ARMAmodel.fit(disp=0)

    y_pred_sarimax = ARMAmodel.get_forecast(len(test_set))
    y_pred_df_sarimax = y_pred_sarimax.conf_int(alpha=0.05)
    y_pred_df_sarimax["Predictions"] = ARMAmodel.predict(start=y_pred_df_sarimax.index[0],end=y_pred_df_sarimax.index[-1])
    y_pred_df_sarimax.index = test_set["date"]
    y_pred_out_sarimax = y_pred_df_sarimax["Predictions"]
    y_pred_out_sarimax.index = range(train_size, len(df))
    df["sarimax"] = y_pred_out_sarimax

    # Second model AMIRAX
    ARIMAmodel = ARIMA(y_train, order=(4, 1, 3))
    ARIMAmodel = ARIMAmodel.fit()

    y_pred_arima = ARIMAmodel.get_forecast(len(test_set["date"]))
    y_pred_df_arima = y_pred_arima.conf_int(alpha=0.05)
    y_pred_df_arima["Predictions"] = ARIMAmodel.predict(start=y_pred_df_arima.index[0], end=y_pred_df_arima.index[-1])
    y_pred_df_arima.index = test_set["date"]
    y_pred_out_arima = y_pred_df_arima["Predictions"]
    y_pred_out_arima.index = range(train_size, len(df))
    df["arima"] = y_pred_out_arima

    # Print graph with the 2 model
    fig = px.line(df, x='date', y=["train", "test", "sarimax", "arima"], title= "Prediction of "+crypto.upper()+" values with SARIMAX and ARMI Models ")
    fig.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)', 'paper_bgcolor': 'rgba(0, 0, 0, 0)'},
                      title_font_color='#E6B11B', legend_font_color="White",  title_x=0.5)

    fig.update_yaxes(showgrid=False, color="White")
    fig.update_xaxes(showgrid=False, color="White")

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


if __name__ == '__main__':
    time.sleep(1)

    # Coonect to MONGODB
    client = MongoClient("mongo",27017)  #Pour le Docker compose
    #client = MongoClient("0.0.0.0", 27017) # for no Docker

    # Create our database
    db = client["coingecko"]

    #Run Flask server
    app.run(host='0.0.0.0', port=5001, use_reloader=False)
