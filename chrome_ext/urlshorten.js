
var get_short_url= function(original_url) {
            var xhr = new XMLHttpRequest();
            xhr.onreadystatechange = handleStateChange;
            xhr.open("POST", "http://aang.in/shorten?orig_url=" + original_url, true);
            xhr.send();
};
var handleStateChange = function() {
    ret_data = JSON.parse(xhr.responseText);
    // Now replace the original field value with the shortened url.i.e: ret_data.url
}
var url_watch =
    function() {
        var text_objs = document.getElementsByTagName("INPUT");
        for (var i=0; i < text_objs.length; ++i) {
            if (text_objs[i].type == "text"){
                text_objs[i].watch('value', shorten_urls);
                }
            }
        };
url_watch();
