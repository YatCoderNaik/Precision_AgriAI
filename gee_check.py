import ee
try:
    ee.Initialize()
    print("Initialize OK")
    print(f"Server check: {ee.String('Success').getInfo()}")
except Exception as e:
    print(f"Error: {e}")
