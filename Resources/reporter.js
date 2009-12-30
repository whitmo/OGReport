var flexspace = Titanium.UI.createButton({
    systemButton:Titanium.UI.iPhone.SystemButton.FLEXIBLE_SPACE
});

var done = Titanium.UI.createButton({
    title:'Done',
    style:Titanium.UI.iPhone.SystemButtonStyle.BORDERED
});

var text_input = Titanium.UI.createTextArea({
    id:'text_input',
    value:'',
    borderStyle:Titanium.UI.INPUT_BORDERSTYLE_ROUNDED,
    height:200,
    width:300,
    keyboardToolbar:[flexspace,done],
    keyboardToolbarHeight: 40
});

done.addEventListener('click',function()
                      {
                          text_input.blur();
			  Titanium.API.info("done button clicked");
		      });

text_input.addEventListener('return', function(e){
                            Titanium.API.info("return button clicked");
});

var report = Titanium.UI.createButton({
    id:'report',
    title:'Report for Location',
    color:'#336699',
    height:40,
    width:200,
    fontSize:12,
    fontWeight:'bold'
});

var camera = Titanium.UI.createButton({
    id:'camera_button',
    title: 'Add Photo',
    image: 'phone-camera.png',
    height:40,
    width:200,
    fontSize:12,
    fontWeight:'bold'
});

var entry_view = Titanium.UI.createWebView({url:'entry.html', name:'entry', image_url:null});

Titanium.UI.currentWindow.addView(entry_view);

function imageUpdate(image){
    if(image != null){
        Titanium.UI.currentWindow.fireEvent("image_update", {image_url:image.url, image:image});
    }
};

function cam_error(error)
{
    // create alert
    var a = Titanium.UI.createAlertDialog();

    // set title
    a.setTitle('Camera Error');

    // set message
    if (error.code == Titanium.Media.NO_CAMERA)
    {
        a.setMessage('Device does not have camera');
    }
    else
    {
        a.setMessage('Unexpected error: ' + error.code);
    }
    a.setButtonNames(['OK']);
    a.show();
};

var current_image = null;

function doReport(e){
    var xhr = Titanium.Network.createHTTPClient();
    xhr.onload = function (e){
            console.log(this.status + " RT:" + this.responseText);
    };
    console.log('clicked report button');
    var position = Titanium.Geolocation.getCurrentPosition(
        function(pos) {
            var coords = pos.coords;
            console.log('Your lonlat is:' + coords.longitude + ' ' + coords.latitude);
            xhr.open('POST', 'http://localhost:8081/spots');
            var payload = {text:text_input.value,
                           latitude:coords.latitude,
                           longitude:coords.longitude,
                           altitude:coords.altitude,
                           accuracy:coords.accuracy,
                           alt_accuracy:coords.altitudeAccuracy,
                           heading:coords.heading,
                           speed:coords.speed,
                           image:current_image};
            xhr.send(payload);
            console.log("payload sent");
        }, {enableHighAccuracy:true});
};
report.addEventListener('click', doReport);

var photo_chooser = Titanium.UI.createOptionDialog();
var photo_options = ["Take Photo", "Choose Photo", "Cancel"];
photo_chooser.setOptions(photo_options);
photo_chooser.setCancel(2);

camera.addEventListener('click', function (e){
    console.log('clicked photo button');
    photo_chooser.show();
});


function handle_image_update(e){
    console.log("photo update: " + e.image_url);
    var info = document.getElementById('info');
    current_image = e.image;
    info.innerHTML = "<img style=\'width:200;margin-bottom:5px\' src='" + e.image_url + "'/>";
}

function handle_chooser(e){
    switch(e.index)
    {
        case 0:
            Titanium.Media.showCamera({
                success:function(image, details){imageUpdate(image);},
                cancel:function(){
                console.log('Cancelled Picture');},
                error:cam_error,
                allowImageEditing:true
            });
            break;
        case 1:
            var options = {
                success: function(image, details){
                    console.log('gallery success');
                    imageUpdate(image);
                },
                error: function(error){
	            Titanium.UI.createAlertDialog( {
		        title: "Error from Gallery",
			message: error.message,
			buttonNames: OK
			    } ).show();
		},
		cancel: function(){}, //@@ add cancel???
		allowImageEditing:true
            };
            Titanium.Media.openPhotoGallery(options);
            break;
    };
}

photo_chooser.addEventListener('click', handle_chooser);


// var wtext = Titanium.UI.createSwitch({
//     id:'with_text',
//     value:switch_vals.text
// });

// wtext.addEventListener('change', function(e){
//     var input = document.getElementById('text_input');
//     switch_vals.text = e.value;
// });

// var wphoto = Titanium.UI.createSwitch({
//     id:'with_photo',
//     value:switch_vals.photo
// });

// wphoto.addEventListener('change', function(e){
//     switch_vals.photo = e.value;
// });