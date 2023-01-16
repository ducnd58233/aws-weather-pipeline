```
exports = function({ query, headers, body}, response) {
    // Data can be extracted from the request as follows:
  
     const decodeBase64 = (s) => {
        var e={},i,b=0,c,x,l=0,a,r='',w=String.fromCharCode,L=s.length
        var A="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        for(i=0;i<64;i++){e[A.charAt(i)]=i}
        for(x=0;x<L;x++){
            c=e[s.charAt(x)];b=(b<<6)+c;l+=6
            while(l>=8){((a=(b>>>(l-=8))&0xff)||(x<(L-2)))&&(r+=w(a))}
        }
        return r
    }
    
    // Headers, e.g. {"Content-Type": ["application/json"]}
    const contentTypes = headers["Content-Type"];

    // Raw request body (if the client sent one).
    // This is a binary object that can be accessed as a string using .text()
    const reqBody = body;

    console.log("Content-Type:", JSON.stringify(contentTypes));
    console.log("Request body:", reqBody);
    // This adds the AWS Headers to the App Services Logs
    console.log("Headers", JSON.stringify(headers));
    
    const firehoseAccessKey = headers["X-Amz-Firehose-Access-Key"];
 
   // Check shared secret is the same to validate Request source, you will create this yourself
   if (firehoseAccessKey == context.values.get("GET_API_KEY")) {
    
    var fullDocument = JSON.parse(body.text());
    
      var collection = context.services.get("mongodb-atlas").db("awspipeline").collection("owm");
      var cnt = 0;
      fullDocument.records.forEach((record) => {
            
            const document = JSON.parse(decodeBase64(record.data))
            console.log("document: " + document)
            console.log("document[0]: " + document[0])
            // const status = collection.insertOne(document[0]);
            const hh = document[0]['Date'].substring(0, 2);
            const status = collection.updateOne({ 'Time': document[0]['Time'], 'Date': {$regex: `/^${hh}/`} }, { $setOnInsert: document[0] }, {upsert: true});
            console.log("got status: "+ status)
            
      })
      
      console.log("Authenticated");
      response.setStatusCode(200);
      const s = JSON.stringify({
                requestId: headers['X-Amz-Firehose-Request-Id'][0],
                timestamp: (new Date()).getTime()
            });
        response.addHeader(
                "Content-Type",
                "application/json"
            );
            response.setBody(s)
            console.log("response JSON:" + s)
        return
   } 
    else {
      console.log("Not Authenticated");
      response.setStatusCode(500);
      response.addHeader("Content-Type","application/json");
      response.setBody(JSON.stringify({
              requestId: headers['X-Amz-Firehose-Request-Id'][0],
              timestamp: (new Date()).getTime(),
              errorMessage: "Error authenticating"
            }))
      return;
    }}
```