function coordToLonlat(coords, from, to, transform){
    // transform is the default, change to make more reusable
    if(from == null){
        to = new OpenLayers.Projection("EPSG:900913");
        from = new OpenLayers.Projection("EPSG:4326");
        console.log('here!!');
    }
    var lonlat = new OpenLayers.LonLat(coords.longitude, coords.latitude);
    lonlat.transform(from, to);
    return lonlat;
}

function activate(key) {
    for(var k in tools) {
        if(k == key) {
            tools[k].activate();
        } else {
            tools[k].deactivate();
        }
    }
}

function register(button) {
    button.addEventListener("click", function() {
        activate(key);
    }, false);
}


var map, vectors, tools;
function map_init(){
    var cw = Titanium.UI.currentWindow;
    map = new OpenLayers.Map('map', {
              controls: [
                  new IOL.Control.Navigation()
              ],
              maxResolution: 156543.03390625,
              maxExtent: new OpenLayers.Bounds(
                      -2.003750834E7,-2.003750834E7,
                      2.003750834E7,2.003750834E7
              ),
              projection: "EPSG:900913",
              numZoomLevels: 7
    });
    cw.olmap = map;
    var wms = new OpenLayers.Layer.WMS(
                  "Base Layer", "http://demo.opengeo.org/geoserver_openstreetmap/gwc/service/wms",
                   {layers: 'openstreetmap',
                   format: 'image/png'
                   }
    );

    map.addLayers([wms]);
    console.log('map created');

    var position = Titanium.Geolocation.getCurrentPosition(
        function(pos) {
            var coords = pos.coords;
            var lonlat = coordToLonlat(pos.coords);
            map.setCenter(lonlat, 6);
            var lonlat = map.getCenter();
            console.log('Your lonlat is:' + lonlat.lon + ' ' +lonlat.lat);
        });
}




// Function activate_control(){

// }

// function createEditingToolbar(){
//     var flex = Titanium.UI.createButton({
// 	systemButton:Titanium.UI.iPhone.SystemButton.FLEXIBLE_SPACE
//     });
//     var navigate =  Titanium.UI.createButton({title:'nav'});
//     var point =  Titanium.UI.createButton({title:'pt'});
//     var line =  Titanium.UI.createButton({title:'line'});
//     var polygon =  Titanium.UI.createButton({title:'pol'});
//     var buttons = [navigate,
//                    flex,
//                    point,
//                    flex,
//                    line,
//                    flex,
//                    polygon];
//     Titanium.UI.currentWindow.setToolbar(buttons, activate_control);
// }



/*
	document.getElementById('hide').onclick = function()
	{
		Titanium.UI.currentWindow.setToolbar(null);
	};
	document.getElementById('show').onclick = function()
	{
		Titanium.UI.currentWindow.setToolbar([a,flexSpace,b,flexSpace,c,flexSpace,d,flexSpace,e]);
	};

*/