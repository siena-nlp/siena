const filesOpen = document.querySelectorAll("div.file-open");
const tabListFiles = document.querySelectorAll("li.tab-files");
const listFilePast = document.querySelectorAll("li.list-file-paste");

function ClosedFiles() {
    for (file of filesOpen) {
        file.style.display = "none";
    };
};

function ClosedTagFile() {
    for (file of tabListFiles) {
        file.className = "tab-files";
    };
};

listFilePast.forEach(file => {
    file.addEventListener("click", () => {
        const value = file.attributes["data-file-name"].value;

        ClosedFiles();
        ClosedTagFile();

        const element = document.querySelector("div.file-open[data-file-name='" + value + "']")
        element.style.display = "block";

        const tab = document.querySelector("li.tab-files[data-file-name='" + value + "']");

        tab.classList.toggle("active");
    });
});

//

$(document).on('mouseenter', '.card-highlighted-text', function () {
    $(this).children('span:nth(0)').css("visibility", "visible");
    $(this).attr("title", $(this).attr("data"));
});
$(document).on('mouseleave', '.card-highlighted-text', function () {
    $(this).children('span:nth(0)').css("visibility", "hidden");
    $(this).removeAttr("title");
});


function getSelected() {
    if (window.getSelection) { return window.getSelection(); }
    else if (document.getSelection) { return document.getSelection(); }
    else {
        var selection = document.selection && document.selection.createRange();
        if (selection.text) { return selection.text; }
        return false;
    }
    return false;
}
$(document).on('mouseup', `div[name='annotation-cell']`, function () {
    // validation
    if($("#context-menu-id").css("display") != "none"){
        return true
    }
    snapSelectionToWord()
    var selection = getSelected();

    if (selection) {
        const text = new String(selection).trim()
        if (text.length > 0) {
            var range = selection.getRangeAt(0);

            range.deleteContents()
            var newNode = document.createElement("div");
            newNode.setAttribute("class", "card-highlighted-text");
            newNode.setAttribute("id", "card-highlighted-text-untagged");
            newNode.setAttribute("name", "highlighted");
            newNode.innerHTML = text + ` <span class="card-highlighted-text-close"><i class="ms-Icon ms-Icon--ChromeClose ms-fontColor-white"></i></span>`;
            range.insertNode(newNode)
            const axis = newNode.getBoundingClientRect()
            var entitiList = ""
            var entitiList = ""
            $.ajax({
                url: "/api/siena/knowledge",
                type: 'POST',
                contentType: "application/json",
                cache: false,
                data: JSON.stringify({
                   TEXT : text.trim()
                }),
                success: function (response) {
                    response = JSON.parse(response)
                    data = response["SUGGESTIONS"]
                    data.forEach(function (item, index) {
                        entitiList += `<li class="context-menu-list-item" name="context-menu-entity-item">${item}</li>`;
                    });


                    document.getElementById("context-menu-entity-list").innerHTML = entitiList;
                    $("#context-menu-id").css("left", axis.x);
                    $("#context-menu-id").css("top", Math.floor(axis.bottom));
                    $("#context-menu-id").css("min-width", Math.ceil(axis.width));
                    $("#context-menu-id").css("display", "block");
                    $("#context-menu-id").data("for-word",text)

                },
                error: function (err) {
                    // range.deleteContents()
                    // range.innerHTML(text)
                    makeNotification("Error","Error occurred while processing your request")
                }
            });
        }

    }
    //unselect
    if (window.getSelection) {
        if (window.getSelection().empty) {  // Chrome
            window.getSelection().empty();
        } else if (window.getSelection().removeAllRanges) {  // Firefox
            window.getSelection().removeAllRanges();
        }
    } else if (document.selection) {  // IE?
        document.selection.empty();
    }

});


function snapSelectionToWord() {
    var sel;

    // Check for existence of window.getSelection() and that it has a
    // modify() method. IE 9 has both selection APIs but no modify() method.
    if (window.getSelection && (sel = window.getSelection()).modify) {
        sel = window.getSelection();
        if (!sel.isCollapsed) {

            // Detect if selection is backwards
            var range = document.createRange();
            range.setStart(sel.anchorNode, sel.anchorOffset);
            range.setEnd(sel.focusNode, sel.focusOffset);
            var backwards = range.collapsed;
            range.detach();

            // modify() works on the focus of the selection
            var endNode = sel.focusNode, endOffset = sel.focusOffset;
            sel.collapse(sel.anchorNode, sel.anchorOffset);

            var direction = [];
            if (backwards) {
                direction = ['backward', 'forward'];
            } else {
                direction = ['forward', 'backward'];
            }

            sel.modify("move", direction[0], "character");
            sel.modify("move", direction[1], "word");
            sel.extend(endNode, endOffset);
            sel.modify("extend", direction[1], "character");
            sel.modify("extend", direction[0], "word");
        }
    } else if ((sel = document.selection) && sel.type != "Control") {
        var textRange = sel.createRange();
        if (textRange.text) {
            textRange.expand("word");
            // Move the end back to not include the word's trailing space(s),
            // if necessary
            while (/\s$/.test(textRange.text)) {
                textRange.moveEnd("character", -1);
            }
            textRange.select();
        }
    }
}
$(document).on('click', `li[name="context-menu-entity-item"]`, function () {
    const clickedEntity = $(this).text()
    const text_highlighted = $("#context-menu-id").data("for-word")
    $("#card-highlighted-text-untagged").attr("data", $(this).html());
    $("#card-highlighted-text-untagged").attr("id", "card-highlighted-text-tagged");
    const sentence_id = $("#card-highlighted-text-tagged").parent().data('s-id')
    const intent = $("#card-highlighted-text-tagged").parent().data('s-intent')
    var $clonedSentence = $("#card-highlighted-text-tagged").removeAttr("id").parent().clone()
    $("#card-highlighted-text-tagged").removeAttr("id");
    $("#context-menu-id").css("display", "none");
    const text = $clonedSentence.html()
    body = {}
    body.data = [
        {
            "id": sentence_id,
            "TEXT": text,
            "INTENT": intent,
            "ENTITY":clickedEntity,
            "HIGHLIGHTED" :text_highlighted,

        },
    ]
    $.ajax({
        url: "/api/siena/sentence",
        type: 'PATCH',
        contentType: "application/json",
        cache: false,
        data: JSON.stringify(body),
        success: function (response) {
            refreshBaseWordList()
        },
        error: function (err) {
            makeNotification("Error","Error occurred while processing your request")
        }
    });
});

$(function () {
    $(document).keydown(function (objEvent) {
        if (objEvent.ctrlKey) {
            if (objEvent.keyCode == 65) {

                return false;
            }
        }
    });
});

$(document).ready(function () {
    $.ajax({
        url: "/api/siena/entity",
        type: 'GET',
        cache: false,
        contentType: false,
        processData: false,
        success: function (response) {
            var text = "";
            const entities = response["ENTITIES"]
            if (!entities) {
                return false
            }
            entities.forEach(function (item) {
                text += `<li class="list-options entity-list" data-entity-name="${item.ENTITY_NAME}" data-entity-replacer="${item.ENTITY_REPLACER}" data-entity-color="${item.ENTITY_COLOR}"><p>${item.ENTITY_NAME}:${item.ENTITY_REPLACER}</p></li>`;
            });
            $('#siena-entity-list').html(text);

        },
        error: function (err) {
            makeNotification("Error","Error occurred while processing your request")
        }
    });

    $.ajax({
        url: "/api/siena/file",
        type: 'GET',
        cache: false,
        contentType: false,
        processData: false,
        success: function (response) {
            const data = JSON.parse(response)
            var text = "";
            const files = data.FILES[0]
            text = files.NAME
            $('#siena-workspace-filename-title').text(text)
            getSentenses()

        },
        error: function (err) {
            makeNotification("Error","Error occurred while processing your request")
        }
    });

    $.ajax({
        url: "/api/siena/navigation",
        type: 'GET',
        cache: false,
        contentType: false,
        processData: false,
        success: function (response) {
            const data = JSON.parse(response)
            var text = "";
            const files = data.FILES
            files.forEach(function (item) {
                text += `<li class="list-options file-list" name="siena-file-name-list" title="${item.PATH}" data-file-id="${item.PATH}" >${item.NAME}</li>`;
            });
            $('#siena-file-list').html(text);
            const documentId = $('#siena-file-list').children().first().data('file-id')
            const fileName = $('#siena-file-list').children().first().text()
            $('#siena-selected-file-id').val(documentId)

        },
        error: function (err) {
            makeNotification("Error","Error occurred while processing your request")
        }
    });

    refreshBaseWordList()

    return false;
});

function refreshBaseWordList(){
    $.ajax({
        url: "/api/siena/knowledge",
        type: 'GET',
        cache: false,
        contentType: false,
        processData: false,
        success: function (response) {
            const data = JSON.parse(response)
            var text = "";
            const BASE_WORDS = data.DATA
            BASE_WORDS.forEach(function (item) {
                text += `<li class="list-options base-word-list" title="${item.entity_name}" name="siena-base-word-list" data-entity-name="${item.entity_name}" data-base-word="${item.base_word}" >${item.base_word}</li>`;
            });
            $('#siena-knowledge-explorer').html(text);

        },
        error: function (err) {
            makeNotification("Error","Error occurred while processing your request")
        }
    });
}


function getSentenses() {
    $.ajax({
        url: "/api/siena/sentence",
        type: 'GET',
        cache: false,
        data: {
            "RANGE_START": 1,
            "RANGE_END": 3,
            "DOCUMENT_ID": "",
        },
        success: function (response) {
            response = JSON.parse(response)
            var text = "";
            const sentences = response["data"]
            sentences.forEach(function (item, index) {
                text += `<div class="card reset-no-select" name="annotation-cell">
            <div class="card-text" data-s-intent="${item['intent']}"  data-s-id="${item['id']}">${item['sentence']}</div>
            </div>`;
            });
            $('#file-open-window').html(text);

        },
        error: function (err) {
            makeNotification("Error","Error occurred while processing your request")
        }
    });
}

$(document).on('click', `#add-new-entity`, function () {
    $('#siena-manage-entities-btn-update').attr("id", "siena-manage-entities-btn-done");
    $("#manage-entity-name").val('')
    $("#manage-entity-replacer-name").val('')
    $("#manage-entity-colour").val('#000000')
    $('#siena-manage-entities').show();
    $("#siena-manage-entities-btn-delete").hide()

});

$(document).on('click', `.card-highlighted-text-close`, function () {
    const text_marked = $(this).parent().text()
    const intent = $(this).parent().parent().data('s-intent')
    const highlightedText = $(this).parent().text()
    const annotatedEntity = $(this).parent().attr("data");
    $(this).parent().parent().attr("id", "siena-temp-cell-mark");
    const sentence_id = $(this).closest('.card-text').data('s-id');
    $(this).parent().replaceWith(text_marked)
    const text = $('#siena-temp-cell-mark').html();
    $('#siena-temp-cell-mark').removeAttr("id");
    if (!annotatedEntity){
        $("#context-menu-id").css("display", "none");
        return false
    }
    body = {}
    body.data = [
        {
            "id": sentence_id,
            "TEXT": text,
            "INTENT": intent,
            "ENTITY":annotatedEntity,
            "HIGHLIGHTED" :highlightedText,
            "MODE" :"ENTITY_REMOVE",
        },
    ]
    $.ajax({
        url: "/api/siena/sentence",
        type: 'PATCH',
        contentType: "application/json",
        cache: false,
        data: JSON.stringify(body),
        success: function (response) {
            refreshBaseWordList()
        },
        error: function (err) {
            makeNotification("Error","Error occurred while processing your request")
        }
    });
});

$(document).on('click', `#siena-manage-entities-btn-cancel`, function () {
    $('#siena-manage-entities').hide();

});

$(document).on('click', `#siena-manage-entities-btn-update`, function () {
    const listIndex = $('#siena-manage-entities').data('list-index');
    const entity_name = $("#manage-entity-name").val()
    const entity_replacer = $("#manage-entity-replacer-name").val()
    const entity_color = $("#manage-entity-colour").val()

    if (!entity_name && !entity_replacer && !entity_color) {
        return false
    }
    else {
        text = `<li class="list-options entity-list" data-entity-name="${entity_name}" data-entity-replacer="${entity_replacer}" data-entity-color="${entity_color}"><p>${entity_name}:${entity_replacer}</p><li>`;
        $("#siena-entity-list li").eq(listIndex).replaceWith(text);
        refreshEntityList();
        $('#siena-manage-entities').hide();
    }

});

$("#siena-entity-list").delegate('li', 'click', function () {
    $("#manage-entity-name").val($(this).data('entity-name'))
    $("#manage-entity-replacer-name").val($(this).data('entity-replacer'))
    $("#manage-entity-colour").val($(this).data('entity-color'))
    $('#siena-manage-entities-btn-done').attr("id", "siena-manage-entities-btn-update");
    $('#siena-manage-entities').data('list-index', $(this).index());
    $('#siena-manage-entities').show();
    $("#siena-manage-entities-btn-delete").show()
});

$(document).on('click', `#siena-manage-entities-btn-done`, function () {
    const entity_name = $("#manage-entity-name").val().trim()
    const entity_replacer = $("#manage-entity-replacer-name").val().trim()
    const entity_color = $("#manage-entity-colour").val().trim()
    if (!entity_name || !entity_replacer || !entity_color) {
        return false
    }
    else {
        text = `<li class="list-options entity-list" data-entity-name="${entity_name}" data-entity-replacer="${entity_replacer}" data-entity-color="${entity_color}"><p>${entity_name}:${entity_replacer}</p><li>`;
        currentEntitylist = String($('#siena-entity-list').html())
        if (!currentEntitylist.includes(text)){
            $('#siena-entity-list').append(text);
        }
        $("#manage-entity-name").val('')
        $("#manage-entity-replacer-name").val('')
        $("#manage-entity-colour").val('#000000')
        refreshEntityList();
        $('#siena-manage-entities').hide();

    }

});

function refreshEntityList() {
    var dataFileds = $('li.entity-list').map(function () {
        data = {}
        data.ENTITY_NAME = $(this).data('entity-name');
        data.ENTITY_REPLACER = $(this).data('entity-replacer');
        data.ENTITY_COLOR = $(this).data('entity-color');
        return data
    }).get();

    postData = {}
    postData.data = dataFileds
    $.ajax({
        url: "/api/siena/entity",
        type: 'POST',
        cache: false,
        data: JSON.stringify(postData),
        contentType: "application/json; charset=utf-8",
        success: function (response) {
            return true
        },
        error: function (err) {
            makeNotification("Error","Error occurred while processing your request")
            return false
        }
    });
}


$(document).on('click', `#siena-workspace-previous`, function () {
    const previous = Number($("#siena-workspace-previous-value").val())
    const next = Number($("#siena-workspace-next-value").val())
    if (previous == 1) {
        return false
    }
    $('#file-open-window').html(`
    <div class="windows8">
    <div class="wBall" id="wBall_1">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_2">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_3">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_4">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_5">
        <div class="wInnerBall"></div>
    </div>
</div>
    `);

    const documentId = $('#siena-selected-file-id').val()
    $.ajax({
        url: "/api/siena/sentence",
        type: 'GET',
        cache: false,
        data: {
            "RANGE_START": previous - 2,
            "RANGE_END": next - 2,
            "DOCUMENT_ID": documentId,
        },
        success: function (response) {
            response = JSON.parse(response)
            var text = "";
            const sentences = response["data"]
            sentences.forEach(function (item, index) {
                text += `<div class="card reset-no-select" name="annotation-cell">
            <div class="card-text"  data-s-id="${item['_id']}">${item['TEXT']}</div>
            </div>`;
            });
            $("#siena-workspace-previous-value").val(previous - 3)
            $("#siena-workspace-next-value").val(previous - 3)
            $('#file-open-window').html(text);
        },
        error: function (err) {
            makeNotification("Error","Error occurred while processing your request")
        }
    });


});

$(document).on('click', `#siena-workspace-next`, function () {
    const previous = Number($("#siena-workspace-previous-value").val())
    const next = Number($("#siena-workspace-next-value").val())
    $('#file-open-window').html(`
    <div class="windows8">
    <div class="wBall" id="wBall_1">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_2">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_3">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_4">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_5">
        <div class="wInnerBall"></div>
    </div>
</div>
    `);
    const documentId = $('#siena-selected-file-id').val()
    $.ajax({
        url: "/api/siena/sentence",
        type: 'GET',
        cache: false,
        data: {
            "RANGE_START": previous + 3,
            "RANGE_END": next + 3,
            "DOCUMENT_ID": documentId,
        },
        success: function (response) {
            response = JSON.parse(response)
            var text = "";
            const sentences = response["data"]
            sentences.forEach(function (item, index) {
                text += `<div class="card reset-no-select" name="annotation-cell">
            <div class="card-text"  data-s-id="${item['_id']}">${item['TEXT']}</div>
            </div>`;
            });
            $("#siena-workspace-previous-value").val(previous + 3)
            $("#siena-workspace-next-value").val(next + 3)
            $('#file-open-window').html(text);

        },
        error: function (err) {
            makeNotification("Error","Error occurred while processing your request");
        }
    });

});

$(document).on('click', `#siena-side-bar-icon-entities`, function () {
    $('#siena-knowledge-side-window').hide();
    $("#siena-side-bar-icon-knowlegde").attr("class", "non-active");
    $('#siena-files-side-window').hide();
    $("#siena-side-bar-icon-files").attr("class", "non-active");
    $('#siena-entity-side-window').show();
    $("#siena-side-bar-icon-entities").attr("class", "active");

});

$(document).on('click', `#siena-side-bar-icon-files`, function () {
    $('#siena-knowledge-side-window').hide();
    $("#siena-side-bar-icon-knowlegde").attr("class", "non-active");
    $('#siena-entity-side-window').hide();
    $("#siena-side-bar-icon-entities").attr("class", "non-active");
    $('#siena-files-side-window').show();
    $("#siena-side-bar-icon-files").attr("class", "active");

});

$(document).on('click', `#siena-side-bar-icon-knowlegde`, function () {
    $('#siena-files-side-window').hide();
    $('#siena-entity-side-window').hide();
    $("#siena-side-bar-icon-files").attr("class", "non-active");
    $("#siena-side-bar-icon-entities").attr("class", "non-active");
    $('#siena-knowledge-side-window').show();
    $("#siena-side-bar-icon-knowlegde").attr("class", "active");

});

$(document).on('click', `li[name="siena-file-name-list"]`, function () {
    const documentPath = $(this).data('file-id');
    docummentName=documentPath.split("/")
    docummentName = docummentName[docummentName.length -1]
    $('#siena-selected-file-id').val(docummentName);
    $('#siena-workspace-filename-title').text(docummentName);
    $('#file-open-window').html(`
    <div class="windows8">
    <div class="wBall" id="wBall_1">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_2">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_3">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_4">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_5">
        <div class="wInnerBall"></div>
    </div>
</div>
    `);
    postData = {}
    postData["FILE_PATH"] = documentPath
    $.ajax({
        url: "/api/siena/fileupload",
        type: 'POST',
        cache: false,
        data: JSON.stringify(postData),
        contentType: "application/json; charset=utf-8",
        success: function (response) {
            getSentenses();
            return true
        },
        error: function (err) {
            makeNotification("Error","Error occurred while processing your request");
            return false
        }
    });
    return true;
});


$(document).on('click', `li[name="siena-base-word-list"]`, function () {
    const baseWord = $(this).data('base-word');
    const entityName = $(this).data('entity-name');
    postData = {}
    $('#file-open-window').html(`
    <div class="windows8">
    <div class="wBall" id="wBall_1">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_2">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_3">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_4">
        <div class="wInnerBall"></div>
    </div>
    <div class="wBall" id="wBall_5">
        <div class="wInnerBall"></div>
    </div>
</div>
    `);
    postData["BASE_WORD"]=baseWord 
    postData["ENTITY"]=entityName
    $.ajax({
        url: "/api/siena/autoannotate",
        type: 'POST',
        cache: false,
        data: JSON.stringify(postData),
        contentType: "application/json; charset=utf-8",
        success: function (response) {
            makeNotification("Success","Auto annotation completed");
            getSentenses();
            return true
        },
        error: function (err) {
            makeNotification("Error","Error occurred while processing your request");
            return false
        }
    });
    return true;
});


function makeNotification(titleText,msgText){
    iziToast.show({
        theme: 'dark',
        backgroundColor: '#3c3c3c',
        position: 'topRight',        title: titleText,
        message: msgText,
    });
}
