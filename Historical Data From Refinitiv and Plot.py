# CONNECT TO REFINITIV API
ek.set_app_key('XXX') ### Place Holder for Refinitiv Key
start = dt.datetime(2019, 1, 29)
end = dt.datetime.today()

#SORT INVESTMENTS BY ASSET CLASS
is_stock_or_etf = (summary_df['Asset Type'] == 'STOCK') | (summary_df['Asset Type'] == 'ETF')
filtered_isin = summary_df.loc[is_stock_or_etf, 'ISIN'].tolist()

# START A REFINITIV SESSION (requires Refititiv to be open in the background)
session = rdp.open_desktop_session('XXX') ### Place Holder for Refinitiv Key
symbologylookup_endpoint = rdp.Endpoint(session,
    'https://api.refinitiv.com/discovery/symbology/v1/lookup')

request_body={
  "from": [
    {
      "identifierTypes": [
        "ISIN"
      ],
      "values": filtered_isin
    }
  ],
  "to": [
    {
      "identifierTypes": [
        "RIC"
      ]
    }
  ],
  "path": [
    {
      "relationshipTypes": [
        "InverseIsValuationQuoteOf"
      ],
      "objectTypes": [
        {
          "from": "AnyInstrument",
          "to": "AnyQuote"
        }
      ]
    }
  ],
  "type": "strict"
}


response = symbologylookup_endpoint.send_request(
    method = rdp.Endpoint.RequestMethod.POST,
    body_parameters = request_body
)

#print(json.dumps(response.data.raw, indent=2))
symboldata = response.data.raw['data']
print(symboldata)
isin_values = []
ric_values = []

for entry in symboldata:
    isin = entry['input'][0]['value']
    ric = entry['output'][0]['value']
    isin_values.append(isin)
    ric_values.append(ric)

ric_df = pd.DataFrame({'ISIN': isin_values, 'RIC': ric_values})

summary_df = summary_df.merge(ric_df, on='ISIN', how='left')
print(summary_df)

#Download Historical Data
df= ek.get_timeseries(ric_values, start_date=start, end_date=end, fields='CLOSE', interval='weekly')

weekly_returns = df.pct_change().dropna()
print(weekly_returns)

#Annualised returns
mus = (1+weekly_returns.mean())**52 - 1
print(mus)

#Covariance
cov = weekly_returns.cov()*52

#-- Create random portfolio weights and indexes
#- How many assests in the portfolio
n_assets = df.shape[1]

mean_variance_pairs = []
weights_list=[]
tickers_list=[]

#Monte Carlo Portfolio Creation
for i in tqdm(range(1000)): #Pick a number of portfolios to create
    next_i = False
    while True:
        #- Choose assets randomly without replacement
        assets = np.random.choice(list(weekly_returns.columns), n_assets, replace=False)
        #- Choose weights randomly ensuring they sum to one
        weights = np.random.rand(n_assets)
        weights = weights/sum(weights)

        #-- Loop over asset pairs and compute portfolio return and variance
        portfolio_E_Variance = 0
        portfolio_E_Return = 0
        for i in range(len(assets)):
            portfolio_E_Return += weights[i] * mus.loc[assets[i]]
            for j in range(len(assets)):
                portfolio_E_Variance += weights[i] * weights[j] * cov.loc[assets[i], assets[j]]

        #-- Skip over dominated portfolios
        for R,V in mean_variance_pairs:
            if (R > portfolio_E_Return) & (V < portfolio_E_Variance):
                next_i = True
                break
        if next_i:
            break

        #-- Add the mean/variance pairs to a list for plotting
        mean_variance_pairs.append([portfolio_E_Return, portfolio_E_Variance])
        weights_list.append(weights)
        tickers_list.append(assets)
        break

mean_variance_pairs = np.array(mean_variance_pairs)

risk_free_rate=0 # Include risk free rate here

# Graphs the Efficient Frontier of the Portfolio
fig = go.Figure()
fig.add_trace(go.Scatter(x=mean_variance_pairs[:,1]**0.5, y=mean_variance_pairs[:,0],
                      marker=dict(color=(mean_variance_pairs[:,0]-risk_free_rate)/(mean_variance_pairs[:,1]**0.5),
                                  showscale=True,
                                  size=7,
                                  line=dict(width=1),
                                  colorscale="RdBu",
                                  colorbar=dict(title="Sharpe<br>Ratio")
                                 ),
                      mode='markers',
                      text=[str(np.array(tickers_list[i])) + "<br>" + str(np.array(weights_list[i]).round(2)) for i in range(len(tickers_list))]))
fig.update_layout(template='plotly_white',
                  xaxis=dict(title='Annualised Risk (Volatility)'),
                  yaxis=dict(title='Annualised Return'),
                  title='Sample of Random Portfolios',
                  width=850,
                  height=500)
fig.update_xaxes(range=[0.18, 0.35])
fig.update_yaxes(range=[0.05,0.29])
fig.update_layout(coloraxis_colorbar=dict(title="Sharpe Ratio"))

fig.show()