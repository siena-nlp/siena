function openFileUploader() {
  document.getElementById('start-step-3-file-upload').click();
}

$("#start-step-3-file-upload-done").on("click", function (evt) {


  $("#start-step-3-file-upload-done").hide()
  $("#start-step-3-loading-animation").show()
  // create project
  body={}
  body.NAME =  $("#siena-selected-project-name").val()
  body.TYPE =  $("#siena-selected-project-type").val()
  body.ENTITIES = []
  $.ajax({
    url: "/API/project",
    type: 'POST',
    data: JSON.stringify(body),
    cache: false,
    contentType: "application/json",
    processData: false,
    success: function (response) {
      const projectId = JSON.parse(response)["PROJECT_ID"]
      const key = `projectId`
      const value = projectId;
      document.cookie = `${key}=${value}`;
      uploadDocument(projectId);
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
      url: "/API/fileUpload",
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
