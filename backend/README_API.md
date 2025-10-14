# Backend API examples

Assumes the FastAPI backend is mounted at `/api/v1` (adjust if different).

1) Upload map (XML file)

curl -X POST "http://localhost:8000/api/v1/map/" -H "accept: application/json" -H "Content-Type: multipart/form-data" -F "file=@path/to/map.xml"

2) Get current map

curl "http://localhost:8000/api/v1/map/"

3) Add a delivery request

curl -X POST "http://localhost:8000/api/v1/requests/" \
  -H "Content-Type: application/json" \
  -d '{"pickup_addr":"25175791","delivery_addr":"25175792","pickup_service_s":120,"delivery_service_s":180}'

4) List requests

curl "http://localhost:8000/api/v1/requests/"

5) Add a courier

curl -X POST "http://localhost:8000/api/v1/couriers/" \
  -H "Content-Type: application/json" \
  -d '{"id":"C1","current_location":{"id":"25175791","latitude":0.0,"longitude":0.0},"name":"Courier 1","phone_number":"+000"}'

6) Compute tours (all couriers)

curl -X POST "http://localhost:8000/api/v1/tours/compute"

7) Get tours

curl "http://localhost:8000/api/v1/tours/"

8) Get combined state

curl "http://localhost:8000/api/v1/state/"

9) Persist state to disk

curl -X POST "http://localhost:8000/api/v1/state/save"

10) Load persisted state

curl -X POST "http://localhost:8000/api/v1/state/load"
