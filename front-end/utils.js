//config
var CFG = {
	host : "http://127.0.0.1:5000",
	debug : true
};

var working_set_cache = null;
//useful functions
function getWorkingSet(refID, callback){
	//check if cached
	if(working_set_cache != null){
		callback.call(window, working_set_cache);
	}
	else{
		console.log("Fetching working set for " + refID);
		//download fresh data
		$.ajax({
			url: CFG.host + "/download",
			dataType: "json",
			type: "POST",
			data: {'reference_id': refID, 'returnAllData': "true"},
			success : function(data, stat, jqXHR){
				working_set_cache = data;
				callback.call(window, data);
			},
		});
	}
}

//index is optional offset if the field is a per-entry field
function getFieldFromData(field, working_set, index){

}