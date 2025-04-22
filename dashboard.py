import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from babel.numbers import format_currency

# Load dataset
@st.cache_data
def load_data():
    df = pd.read_csv("all_data.csv")
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])
    df["order_date"] = df["order_purchase_timestamp"].dt.date
    return df

def create_daily_orders_df(df):
    daily_orders_df = df.resample(rule='D', on='order_purchase_timestamp').agg({
        "order_id": "nunique",
        "payment_value": "sum"
    }).reset_index()
    daily_orders_df.rename(columns={
        "order_id": "order_count",
        "payment_value": "revenue"
    }, inplace=True)
    return daily_orders_df

def create_sum_order_items_df(df):
    return df.groupby("product_category_name").order_item_id.sum().sort_values(ascending=False).reset_index()

def create_rfm_df(df):
    rfm_df = df.groupby(by="customer_id", as_index=False).agg({
        "order_purchase_timestamp": "max",
        "order_id": "nunique",
        "payment_value": "sum"
    })
    rfm_df.columns = ["customer_id", "max_order_timestamp", "frequency", "monetary"]
    rfm_df["max_order_timestamp"] = rfm_df["max_order_timestamp"].dt.date
    recent_date = df["order_purchase_timestamp"].dt.date.max()
    rfm_df["recency"] = rfm_df["max_order_timestamp"].apply(lambda x: (recent_date - x).days)
    rfm_df.drop("max_order_timestamp", axis=1, inplace=True)
    return rfm_df

data = load_data()

st.sidebar.header("Filter Data")
st.sidebar.image("https://pbs.twimg.com/profile_images/943515781/apres_400x400.jpg")
selected_city = st.sidebar.multiselect("City", data["customer_city"].unique())
selected_category = st.sidebar.multiselect("Product Category", data["product_category_name"].unique())

start_date = st.sidebar.date_input("From This", data["order_purchase_timestamp"].min().date())
end_date = st.sidebar.date_input("To This", data["order_purchase_timestamp"].max().date())

date_filtered = data[
    (data["order_purchase_timestamp"].dt.date >= start_date) &
    (data["order_purchase_timestamp"].dt.date <= end_date)
]
top5_cities = data["customer_city"].value_counts().head(5).index
city_data = date_filtered[date_filtered["customer_city"].isin(top5_cities)]


# Filter utama
filtered_data = data.copy()
if selected_city:
    filtered_data = filtered_data[filtered_data["customer_city"].isin(selected_city)]
if selected_category:
    filtered_data = filtered_data[filtered_data["product_category_name"].isin(selected_category)]
filtered_data = filtered_data[
    (filtered_data["order_purchase_timestamp"].dt.date >= start_date) &
    (filtered_data["order_purchase_timestamp"].dt.date <= end_date)
]

# Jika data kosong
if filtered_data.empty:
    st.warning("Data tidak ditemukan untuk filter yang dipilih.")
    st.stop()

st.title("📊 Dashboard Analisis E-Commerce")

main_df = filtered_data.copy()
daily_orders_df = create_daily_orders_df(main_df)
sum_order_items_df = create_sum_order_items_df(main_df)
rfm_df = create_rfm_df(main_df)

st.subheader('Orders')

col1, col2 = st.columns(2)
with col1:
    total_orders = daily_orders_df.order_count.sum()
    st.metric("Total Orders", value=total_orders)

with col2:
    total_revenue = format_currency(daily_orders_df.revenue.sum(), "BRL", locale='pt_BR')
    st.metric("Total Revenue", value=total_revenue)

fig, ax = plt.subplots(figsize=(16, 6))
ax.plot(daily_orders_df["order_purchase_timestamp"], daily_orders_df["order_count"], marker='o', color="#90CAF9")
ax.set_title("Order Tren")
st.pyplot(fig)

fig_rev, ax_rev = plt.subplots(figsize=(16, 6))
ax_rev.plot(daily_orders_df["order_purchase_timestamp"], daily_orders_df["revenue"], marker='o', color="#FFB74D")
ax_rev.set_title("Revenue Tren")
st.pyplot(fig_rev)

st.subheader("Customer Distribution Based on City")
top_cities = filtered_data["customer_city"].value_counts().head(10)
fig1, ax1 = plt.subplots(figsize=(10, 5))
sns.barplot(x=top_cities.index, y=top_cities.values, ax=ax1)
ax1.set_ylabel("Jumlah Pelanggan")
plt.xticks(rotation=45)
st.pyplot(fig1)

top_5_cities = filtered_data["customer_city"].value_counts().head(5).index

st.subheader("Top 5 city Based on Order")
orders_trend = city_data.groupby(
    [city_data["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp(), "customer_city"]
).size().unstack().fillna(0)
st.line_chart(orders_trend)

st.subheader("Top 5 City Based on Revenue")
revenue_trend = city_data.groupby(
    [city_data["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp(), "customer_city"]
)["payment_value"].sum().unstack().fillna(0)
st.line_chart(revenue_trend)

st.subheader("Metode Pembayaran yang Paling Dipakai")
payment_counts = filtered_data["payment_type"].value_counts()
st.bar_chart(payment_counts)


st.subheader("Best & Worst Performing Product")

fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(30, 10))
colors = ["#90CAF9"] + ["#D3D3D3"]*4

sns.barplot(x="order_item_id", y="product_category_name", data=sum_order_items_df.head(5), palette=colors, ax=ax[0])
ax[0].set_title("Best Performing Product")
ax[0].set_xlabel("Number of Sales")

sns.barplot(x="order_item_id", y="product_category_name", data=sum_order_items_df.sort_values(by="order_item_id", ascending=True).head(5), palette=colors, ax=ax[1])
ax[1].set_title("Worst Performing Product")
ax[1].set_xlabel("Number of Sales")

st.pyplot(fig)

st.subheader("Revenue Distribution Based on Product Category")
revenue_by_category = filtered_data.groupby("product_category_name")["payment_value"].sum().sort_values(ascending=False).head(10)
fig2, ax2 = plt.subplots(figsize=(10, 5))
sns.barplot(x=revenue_by_category.values, y=revenue_by_category.index, ax=ax2)
ax2.set_xlabel("Total Revenue")
st.pyplot(fig2)

st.subheader("Seller Perform")
seller_perf = filtered_data.groupby("seller_id")["payment_value"].sum().sort_values(ascending=False).head(10)
fig3, ax3 = plt.subplots(figsize=(10, 5))
sns.barplot(x=seller_perf.values, y=seller_perf.index, ax=ax3)
ax3.set_xlabel("Total Revenue")
ax3.set_ylabel("Seller ID")
st.pyplot(fig3)

seller_orders = filtered_data.groupby("seller_id")["order_id"].nunique().sort_values(ascending=False).head(10)
fig4b, ax4b = plt.subplots(figsize=(10, 5))
sns.barplot(x=seller_orders.values, y=seller_orders.index, ax=ax4b)
ax4b.set_xlabel("Total Order")
ax4b.set_ylabel("Seller ID")
ax4b.set_title("Worst Seller Performing")
st.pyplot(fig4b)

st.subheader("Best Customer Based on RFM")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Avg Recency (days)", value=round(rfm_df.recency.mean(), 1))
with col2:
    st.metric("Avg Frequency", value=round(rfm_df.frequency.mean(), 2))
with col3:
    st.metric("Avg Monetary", value=format_currency(rfm_df.monetary.mean(), "AUD", locale='es_CO'))

fig4, ax4 = plt.subplots(1, 3, figsize=(35, 10))
colors = ["#90CAF9"] * 5

sns.barplot(y="recency", x="customer_id", data=rfm_df.sort_values(by="recency").head(5), palette=colors, ax=ax4[0])
ax4[0].set_title("By Recency")

sns.barplot(y="frequency", x="customer_id", data=rfm_df.sort_values(by="frequency", ascending=False).head(5), palette=colors, ax=ax4[1])
ax4[1].set_title("By Frequency")

sns.barplot(y="monetary", x="customer_id", data=rfm_df.sort_values(by="monetary", ascending=False).head(5), palette=colors, ax=ax4[2])
ax4[2].set_title("By Monetary")
for ax in ax4:
    ax.tick_params(axis='x', labelrotation=45)
st.pyplot(fig4)

st.caption("Ipan Apres!")
