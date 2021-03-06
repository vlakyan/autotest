import {JetView} from "webix-jet";
import MenuView from "views/top";
import {iterationCopy, getJenkinsLink} from "utils/func"
import {beta_url} from "models/beta"
import {help_button, handleHelpPopup} from "models/templates"

export default class SessionListView extends JetView{
	config(){

	    document.title = "Sessions list"

        var addButton = {
            view:"button",
            type:"icon",
            icon:"mdi mdi-new-box",
            label:"Create",
            width: 80,
            align: "left",
        }

        var grid = {
          view:"datatable",
          select:"row",
          columns:[
              {id:"build_number", template: "", header:"Build number",width:70, sort:"integer", dataIndex: "build_number"},
              {id:"causedby", template: "", header:"Caused by",width:180, sort:"string"},
              {id:"version", header:"Release",fillspace:true, sort:"string", template:""},
              {id:"device_name", header:"Device ID",width:180, sort:"string", dataIndex: "device_name"},
              {id:"time_start", header:"Start time",width:150, sort:"string", dataIndex: "time_start"},
              {id:"time_end", header:"End time",width:150,sort:"string", dataIndex: "time_end"},
              {id:"status", name: "status", header:"Status", sort:"string",width:80, dataIndex: "status" },
              {id: "test_pie", name: "test_pie", header: "Tests", width: 100},
              {id: "actions", header: "Actions", fillspace:true, template:"{common.trashIcon()}" }],
            onClick:{

                "wxi-trash":function(ev, id){

                    var test = this.getItem(id.row).build_number

                    var confirmDelete = {
                        view:"window",
                        id: "confirm_delete",
                        modal:true,
                        position:"center",
                        height:250,
                        width:300,
                        head: { view: "label", template: function(){
                               return "Delete session " + test + "?"
                            }},
                        body: {
                            cols: [
                                {view:"button", label:"OK", click: () =>
                                    {
                                        webix.ajax().bind(this).del(beta_url + "/session/"+id.row, function(text, xml, xhr){
                                            $$('confirm_delete').close();
                                            this.$scope.refresh();
                                        });
                                    }
                                },
                                {view:"button", label:"Close", click:("$$('confirm_delete').close();")}
                            ]
                        }
                    }
                    webix.ui(confirmDelete).show();
                    return false;
                 }
            }
        }

        function get_grid(type) {
            var new_grid = iterationCopy(grid);
            new_grid.id = "mytable_" + type
            new_grid.url = beta_url + "/session/" + type
            return new_grid;
        };

        function get_addButton(type) {
            var new_button = iterationCopy(addButton);
            new_button.click = function() {this.$scope.show("/top/createsession?type=" + type);}
            return new_button;
        };

        var tabview = { view:"tabview",
          cells:[
            {
              header:"UI",
              body:{type: "layout",
               rows: [
               {cols: [ get_addButton("ui"), help_button]},
               get_grid("ui")
              ]}
             },
            {
              header:"Hardware",
              body:{type: "layout",
               rows: [
               get_addButton("hardware"),
               get_grid("hardware")
              ]}
            }
          ]
        }

       return tabview;
	}

	init() {

	    $$("help_button").attachEvent("onItemClick", function(){
	        handleHelpPopup("help_button", "help_popup", "Here you can start a new test session!")
	    })

        function getCause(started_by, job, build_num, url) {
            if (job != null && job != ""){
                return "<span>Job " + job + "&nbsp;<a href=\"" + url + "\">#" + build_num + "</a></span>"
            }
            if (started_by != null && started_by != "") {
                return "Started by " + started_by
            }
            return null
        }

        function handle_statuses(id) {


            $$(id).attachEvent("onAfterLoad", function(){
                $$(id).eachRow(function(row){
                    var record = $$(id).getItem(row);
                    var css = null
                    var cause = getCause(record.caused_by, record.upstream_job, record.upstream_build_number, record.upstream_url);
                    if (record.status == "Passed") css = "status_passed";
                    if (record.status == "Failed") css = "status_failed";
                    if (record.status == "In progress") css = "status_inprogress";
                    $$(id).addCellCss(record.id, "status", css);

                    $$(id).mapCells(record.id,"causedby",1,1,
                        function(value, row_id, column_id, row_ind, col_ind){
                            return cause;
                     });
                    var jenkins = getJenkinsLink("hardware", record.build_number)
                 if (record.hasOwnProperty("jenkins_job")) {
                    jenkins = getJenkinsLink("hardware", record.build_number, record.jenkins_job)

                 }
                 $$(id).mapCells(record.id,"build_number",1,1,
                        function(value, row_id, column_id, row_ind, col_ind){
                            return jenkins;
                     });
                     $$(id).mapCells(record.id,"version",1,1,
                        function(value, row_id, column_id, row_ind, col_ind){
                            if (value!=null) return value.version
                            else return record.release
                     });
                    $$(id).refresh();
            }, true);



            });

            $$(id).attachEvent("onAfterSelect", function(selection, preserve){
                this.$scope.show("/top/session.hardware?id=" + selection.id)
            })
        }

        handle_statuses("mytable_ui");
        handle_statuses("mytable_hardware");
	}
};