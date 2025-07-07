curl -X POST "http://localhost/AT/ussd/setup" -H "accept: */*"
curl -X POST "http://localhost/ussd/partner/" -H "accept: */*" -H "Content-Type: application/json" -d "{\"partnerId\":\"1000\",\"partnerUrl\":\"http://localhost:8080/credentials/\",\"partnerKey\":\"abc123\"}"
