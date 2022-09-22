function openFileUploader() {
  document.getElementById('start-step-3-file-upload').click();
}

$("#start-step-3-file-upload-done").on("click", function (evt) {
  $("#start-step-3-file-upload-done").hide()
  $("#start-step-3-loading-animation").show()
    //upload document
    var documentData = new FormData();
    console.log($('#start-step-3-file-upload')[0].files)
    documentData.append('file', $('#start-step-3-file-upload')[0].files[0]);
    $.ajax({
      url: "/api/siena/fileupload",
      type: 'POST',
      data: documentData,
      cache: false,
      contentType: false,
      processData: false,
      success: function (response) {
        $('#start-step-3-file-upload-form').hide();
        $('#start-step-4').show()
      }
    });
  return false;
});

function uploadDocument(path){
    //upload document
    var documentData = new FormData();
    documentData.append('file', $('#start-step-3-file-upload')[0].files[0]);
    documentData.append('FILE_PATH', path);
    $.ajax({
      url: "/api/siena/fileUpload",
      type: 'POST',
      data: documentData,
      cache: false,
      contentType: false,
      processData: false,
      success: function (response) {
        $('#start-step-3-file-upload-form').hide();
        $('#start-step-4').show()
  
      }
    });
}


$("#start-step-1-new-project").on("click", function (evt) {
  $("#start-step-1").hide();
  $("#start-step-3-file-upload-form").show();
  return true;
});

$("#start-step-1-existing-project").on("click", function (evt) {
  document.location.href = "/siena";
  return true;
});

$(`div[name="start-step-2-framework"]`).on("click", function (evt) {
  const projectName = $("#start-step-2-project-name").val()
  if (!projectName){
    $("#start-step-2-project-name").css("border","1px solid #DF362D")
    return false
  }
  $("#start-step-2").hide();
  $("#start-step-3-file-upload-form").show();
  $("#siena-selected-project-type").val($(this).data("framework-name"));
  $("#siena-selected-project-name").val(projectName);
  return true;
});

$(document).on('click', `div[name="start-step-5-project-tile"]`, function () {
  const key = `projectId`
  const value = $(this).data('project-id');
  document.cookie = `${key}=${value}`;
  window.location.href = '/siena';
  return true;
});
