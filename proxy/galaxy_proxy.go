package main

import (
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "flag"
    "fmt"
    "io/ioutil"
    "os"
    "time"
    "net/url"
    "net/http"
    "github.com/gin-contrib/location"
    "github.com/gin-gonic/gin"
)


var upstream_baseurl string = "https://galaxy.ansible.com"
type GalaxyProxy struct {}


type GalaxyResponse struct {
    Code    int
    Url     string
	Headers	string
	Body    string
    Fetched string
}


func hash(s string) string{
    // make a hexified sha56sum from a string
    hasher := sha256.New()
    hasher.Write([]byte(s))
    sha := hex.EncodeToString(hasher.Sum(nil))
	return string(sha)
}


func join_params(query_params url.Values) string {
    // naive string join for a query parameters map
    param_string := ""
    cnt := 0 
    for key, val := range query_params {
        if len(query_params) == 0 {
            param_string += string(key) + "=" + val[0]
        } else if cnt == 0 {
            param_string += string(key) + "=" + val[0]
        } else {
            param_string += "&" + string(key) + "=" + val[0]
        }
        cnt++
    }
    return param_string
}

func get_upstream_url(url_path string, query_params url.Values) GalaxyResponse {

    /*****************************************************
     *  Get a request from cache or forward to upstream 
     ****************************************************/

    // assemble the url
    upstream_url := upstream_baseurl + url_path
    param_string := join_params(query_params)
    if len(param_string) > 0 {
        upstream_url += "?" + param_string
    }

    // make a hash of this url ...
    fhash := hash(upstream_url)
    fprefix := fhash[0:3]

    // define the cache filename ...
    fdir := ".cache/" + fprefix
    fname := fdir + "/" + fhash + ".json"

    // make cache directory if not exists ...
    if _, err := os.ReadDir(fdir); err != nil {
        os.MkdirAll(fdir, 0755)
    }

    // use cache file if exists ...
    if _, err := os.Stat(fname); err == nil {
        fmt.Println("CACHE HIT " + upstream_url + " > " + fname)
        jsonFile, _ := os.Open(fname)
        byteValue, _ := ioutil.ReadAll(jsonFile)
        var resp GalaxyResponse
        json.Unmarshal(byteValue, &resp)
        jsonFile.Close()
        return resp
    }

    // fetch the data ...
    fmt.Println("CACHE MISS " + upstream_url + " > " + fname)
    t1 := time.Now()
    uresp, _ := http.Get(upstream_url)
    t2 := time.Now()
    diff := t2.Sub(t1)
    fmt.Println(diff)

    // munge the body and headers
    body, _ := ioutil.ReadAll(uresp.Body)
    sb := string(body)
    jsonStr, _ := json.Marshal(uresp.Header)
    sj := string(jsonStr)

    // construct the response
	resp := GalaxyResponse{
        Code: uresp.StatusCode,
        Headers: sj,
        Body: sb,
        Url: upstream_url,
        Fetched: time.Now().Format(time.RFC3339),
    }

    // store response on disk
    fileJson, _ := json.MarshalIndent(resp, "", " ")
    ioutil.WriteFile(fname, fileJson, 0644)
    
    // return
	return resp
}


func (g *GalaxyProxy) Api(c *gin.Context) {
	c.JSON(200, gin.H{
		"available_versions": gin.H{
			"v1": "v1/",
			"v2": "v2/",
			"v3": "v3/",
		},
		"current_version": "v1",
		"description": "Galaxy Proxy",
	})
}


func (g *GalaxyProxy) UpstreamHandler(c *gin.Context) {

    /*************************************
     * Handle api/v1/roles/*
     ************************************/

    // get the upstream response ...
	url_path := c.Request.URL.Path
	uresp := get_upstream_url(url_path, c.Request.URL.Query())

    // set response headers ...
    var headers map[string]string
    json.Unmarshal([]byte(uresp.Headers), &headers)
    for k,v := range headers {
        c.Request.Header.Add(k, v)
    }

    // return the body ...
    c.String(uresp.Code, uresp.Body)
}


func main() {
    var artifacts string
    var port string
    galaxy_proxy := GalaxyProxy{}

    flag.StringVar(&artifacts, "artifacts", "artifacts", "Location of the artifacts dir")
    flag.StringVar(&port, "port", "8080", "Port")
    flag.Parse()

    r := gin.Default()
    r.RedirectTrailingSlash = true
    r.Use(location.Default())

    // api root
    r.GET("/api/", galaxy_proxy.Api)

    // v1
    r.GET("/api/v1/users/", galaxy_proxy.UpstreamHandler)
    r.GET("/api/v1/namespaces/", galaxy_proxy.UpstreamHandler)
    r.GET("/api/v1/roles/", galaxy_proxy.UpstreamHandler)
    r.GET("/api/v1/roles/:roleid/", galaxy_proxy.UpstreamHandler)
    r.GET("/api/v1/roles/:roleid/versions/", galaxy_proxy.UpstreamHandler)

    /*
    r.GET("/api/", amanda.Api)
    r.GET("/api/v2/collections/", amanda.Collections)
    r.GET("/api/v2/collections/:namespace/:name/", amanda.Collection)
    r.GET("/api/v2/collections/:namespace/:name/versions/", amanda.Versions)
    r.GET("/api/v2/collections/:namespace/:name/versions/:version/", amanda.Version)
    */

    //r.Static("/artifacts", amanda.Artifacts)
    r.Run(":" + port)
}
