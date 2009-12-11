function Bag(){};

window.onload = function(){
        //var tools = Titanium.UI.createWindow({url:'tools.html', title:'Drawing Tools'});
        var appstate = new Bag();
        var olmap = Titanium.UI.createWebView({url:'map.html', name:'olmap', appstate:appstate});
        var tools = Titanium.UI.createWebView({url:'tools.html', name:'tools', appstate:appstate});
        var compose = Titanium.UI.createButton({systemButton:Titanium.UI.iPhone.SystemButton.COMPOSE});
        var done = Titanium.UI.createButton({systemButton:Titanium.UI.iPhone.SystemButton.DONE});
	compose.addEventListener('click',
            function(){
                //
	        Titanium.UI.currentWindow.setRightNavButton(done);
                Titanium.UI.currentWindow.showView(tools, {animated:false});
            }
        );
        done.addEventListener('click',
                              function(){
                                  Titanium.UI.currentWindow.showView(olmap, {animated:true});
                                  Titanium.UI.currentWindow.setRightNavButton(compose);
                              });
	Titanium.UI.currentWindow.setRightNavButton(compose);
        Titanium.UI.currentWindow.addView(olmap);
        Titanium.UI.currentWindow.addView(tools);
        Titanium.UI.currentWindow.showView(olmap, {animated:false});
        Titanium.API.info(Titanium.UI.currentWindow + " is ready");
};


