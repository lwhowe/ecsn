// jquery
$(function() {
    // toggle visibility of user-menu element
  $('#user-name').hover(function() {
    $('#user-menu').css('visibility', 'visible');
  }, function() {
    $('#user-menu').css('visibility', 'hidden');  // on mouseout
  });
  $('#user-menu').hover(function() {
    $('#user-menu').css('visibility', 'visible');
  }, function() {
    $('#user-menu').css('visibility', 'hidden');  // on mouseout
  });
});

$(document).ready(function(){
    // datepicker ui
    $(".datepick").datepicker();

    // ajax post for class 'ctrl'
    $(".ctrl").on('change', function(e){
        var optionSelected = $(this).find("option:selected");
        var valueSelected  = optionSelected.val();
        var textSelected   = optionSelected.text();
        var machineName = $(this).parent().children("li.title").text()

        if ($(this).parent().children().eq(2).text().indexOf('Standalone') >= 0){
            var machineType = "standalone-cimc";
        } else if ($(this).parent().children().eq(2).text().indexOf('Virtual') >= 0){
            var machineType = "virtual-host";
        }

        $.post("/",
        {
            mname: machineName,
            mtype: machineType,
            state: valueSelected
        },
        function(response){
            if (response['status'] == 'success'){
                alert(machineName + ":\n" + textSelected + " successfully");}
            else {
                if (typeof response['message'] == "undefined"){
                    alert(machineName + ":\n" + "No response from server, check with web admin");
                } else {
                    alert(machineName + ":\n" + response['message']);
                }
            }
        });
    });

    // ajax post for class 'ctrl2'
    $(".ctrl2").on('change', function(e){
        var optionSelected = $(this).find("option:selected");
        var valueSelected  = optionSelected.val();
        var textSelected   = optionSelected.text();
        var machineName = $(this).parent().children("div.machine").eq(0).children().children("li.title").text();

        if (textSelected.indexOf('CIMC:') >= 0){
            var machineType = "virtual-cimc";
        } else if (textSelected.indexOf('ESXI:') >= 0){
            var machineType = "virtual-esxi";
        }

        $.post("/",
        {
            mname: machineName,
            mtype: machineType,
            state: valueSelected
        },
        function(response){
            if (response['status'] == 'success'){
                alert(textSelected + " successfully");}
            else {
                if (typeof response['message'] == "undefined"){
                    alert("No response from server, check with web admin");
                } else {
                    alert(response['message']);
                }
            }
        });
    });

    // cancel and redirect from editing the config page
    $("#cfg-cancel").click(function(){
        window.location.replace(window.location.href.replace(/&?edit=([^&]$|[^&]*)/i, ""));  // http redirect
    });
});

// javascript
function openTab(evt, tabName) {
    // Declare all variables
    var i, tabcontent, tablinks;

    // Get all elements with class="tabcontent" and hide them
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }

    // Get all elements with class="tablinks" and remove the class "active"
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }

    // Show the current tab, and add an "active" class to the link that opened the tab
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}
