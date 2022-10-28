package main

import (
	//"archive/tar"
	//"compress/gzip"
	//"crypto/sha256"
    "crypto/sha256"
    //"encoding/base64"
    "encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
    //"hash/fnv"
	//"io"
	"io/ioutil"
	//"log"
	"os"
	//"path/filepath"
    //"reflect"
	//"sort"
    //"strconv"
	//"strings"
	"time"
	"net/url"
    "net/http"

	//"github.com/Masterminds/semver/v3"
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


/*
func hash(s string) string {
    h := fnv.New32a()
    h.Write([]byte(s))
    return fmt.Sprint(h.Sum32())
}
*/

func hash(s string) string{
    hasher := sha256.New()
    hasher.Write([]byte(s))
    //sha := base64.URLEncoding.EncodeToString(hasher.Sum(nil))
    sha := hex.EncodeToString(hasher.Sum(nil))
	return string(sha)
}


func join_params(query_params url.Values) string {
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


func (g *GalaxyProxy) Roles(c *gin.Context) {

    // get the usptream response ...
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
	//var err error
	galaxy_proxy := GalaxyProxy{}

	flag.StringVar(&artifacts, "artifacts", "artifacts", "Location of the artifacts dir")
	flag.StringVar(&port, "port", "8080", "Port")
	flag.Parse()

    /*
	amanda.Artifacts, err = filepath.Abs(artifacts)
	if err != nil {
		log.Fatal(err)
	}
    */

	r := gin.Default()
	r.RedirectTrailingSlash = true
	r.Use(location.Default())

    /*
	r.GET("/api/", amanda.Api)
	r.GET("/api/v2/collections/", amanda.Collections)
	r.GET("/api/v2/collections/:namespace/:name/", amanda.Collection)
	r.GET("/api/v2/collections/:namespace/:name/versions/", amanda.Versions)
	r.GET("/api/v2/collections/:namespace/:name/versions/:version/", amanda.Version)
    */

	r.GET("/api/", galaxy_proxy.Api)
    r.GET("/api/v1/roles/", galaxy_proxy.Roles)
    r.GET("/api/v1/roles/:roleid/", galaxy_proxy.Roles)
    r.GET("/api/v1/roles/:roleid/versions/", galaxy_proxy.Roles)

	//r.Static("/artifacts", amanda.Artifacts)
	r.Run(":" + port)
}
