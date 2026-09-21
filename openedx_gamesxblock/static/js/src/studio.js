/* Studio editor (studio_view) for the Games XBlock. One editor covers every
 * game_type -- switching the dropdown shows/hides the relevant content
 * section, and Save only sends the fields relevant to the selected type
 * (handled server-side too, so switching types never destroys other
 * previously authored content). */
function GamesXBlockStudio(runtime, element) {
    'use strict';

    var root = $('#gx-studio', element)[0];
    var gameTypeSelect = $('#gx-studio-game-type', element)[0];
    var gradedFieldset = $('#gx-studio-graded-fields', element)[0];
    var timerField = $('#gx-studio-timer-field', element)[0];
    var statusEl = $('#gx-studio-status', element)[0];
    var saveUrl = runtime.handlerUrl(element, 'save_settings');
    var uploadUrl = runtime.handlerUrl(element, 'upload_image');

    var GRADED_TYPES = ['matching', 'sequencing', 'cloze'];
    var TIMER_TYPES = ['word_search', 'memory'];

    // Initial content, injected by the server render as a JSON blob scoped to
    // this element (never on `window`, so multiple blocks on one page can't
    // clobber each other's data).
    var initialDataEl = $('#gx-studio-initial-data', element)[0];
    var initialData = { cards: [], sequence_items: [], cloze_blanks: [], wordsearch_words: [], memory_pairs: [] };
    if (initialDataEl) {
        try {
            initialData = JSON.parse(initialDataEl.textContent);
        } catch (e) {
            // Malformed/missing initial data -- fall back to empty sections rather than breaking the editor.
        }
    }

    var repeatables = {
        cards: { containerId: 'gx-studio-cards', templateId: 'gx-card-row-template' },
        sequence_items: { containerId: 'gx-studio-sequence-items', templateId: 'gx-sequence-row-template' },
        cloze_blanks: { containerId: 'gx-studio-cloze-blanks', templateId: 'gx-blank-row-template' },
        wordsearch_words: { containerId: 'gx-studio-wordsearch-words', templateId: 'gx-word-row-template' },
        memory_pairs: { containerId: 'gx-studio-memory-pairs', templateId: 'gx-memory-row-template' },
    };

    function templateFor(key) {
        return $(element).find('#' + repeatables[key].templateId)[0];
    }
    function containerFor(key) {
        return $(element).find('#' + repeatables[key].containerId)[0];
    }

    function addRow(key, values) {
        var template = templateFor(key);
        var container = containerFor(key);
        var rowEl = template.content.firstElementChild.cloneNode(true);

        if (values) {
            Array.prototype.forEach.call(rowEl.querySelectorAll('[data-field]'), function (input) {
                var field = input.getAttribute('data-field');
                if (field === 'answers' || field === 'distractors') {
                    input.value = (values[field] || []).join(', ');
                } else if (values[field] !== undefined) {
                    input.value = values[field];
                }
            });
            rowEl.setAttribute('data-existing-id', values.card_id || values.item_id || values.pair_id || '');
        }

        var removeBtn = rowEl.querySelector('.gx-studio-remove');
        if (removeBtn) {
            removeBtn.addEventListener('click', function () {
                rowEl.remove();
                renumberRows(key);
            });
        }
        var upBtn = rowEl.querySelector('.gx-studio-move-up');
        var downBtn = rowEl.querySelector('.gx-studio-move-down');
        if (upBtn) {
            upBtn.addEventListener('click', function () {
                var prev = rowEl.previousElementSibling;
                if (prev) { container.insertBefore(rowEl, prev); renumberRows(key); }
            });
        }
        if (downBtn) {
            downBtn.addEventListener('click', function () {
                var next = rowEl.nextElementSibling;
                if (next) { container.insertBefore(next, rowEl); renumberRows(key); }
            });
        }
        Array.prototype.forEach.call(rowEl.querySelectorAll('.gx-studio-upload'), function (btn) {
            btn.addEventListener('click', function () { triggerImageUpload(rowEl, btn.getAttribute('data-upload-for')); });
        });

        container.appendChild(rowEl);
        renumberRows(key);
    }

    function renumberRows(key) {
        var container = containerFor(key);
        Array.prototype.forEach.call(container.querySelectorAll('.gx-studio-row-index'), function (el, idx) {
            el.textContent = (idx + 1) + '.';
        });
    }

    function triggerImageUpload(rowEl, fieldName) {
        var fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'image/*';
        fileInput.addEventListener('change', function () {
            if (!fileInput.files || !fileInput.files[0]) { return; }
            var formData = new FormData();
            formData.append('file', fileInput.files[0]);

            $.ajax({
                type: 'POST',
                url: uploadUrl,
                data: formData,
                processData: false,
                contentType: false,
                dataType: 'json',
                success: function (response) {
                    if (response.success) {
                        rowEl.querySelector('[data-field="' + fieldName + '"]').value = response.url;
                    } else {
                        setStatus(response.error || 'Upload failed.', true);
                    }
                },
                error: function () { setStatus('Upload failed.', true); },
            });
        });
        fileInput.click();
    }

    // Seed each repeatable section with any previously authored content.
    Object.keys(repeatables).forEach(function (key) {
        (initialData[key] || []).forEach(function (values) { addRow(key, values); });
    });

    Array.prototype.forEach.call($(element).find('[data-add]'), function (btn) {
        btn.addEventListener('click', function () { addRow(btn.getAttribute('data-add'), null); });
    });

    function updateVisibleSection() {
        var selected = gameTypeSelect.value;
        Array.prototype.forEach.call(root.querySelectorAll('[data-game-section]'), function (section) {
            section.classList.toggle('gx-active', section.getAttribute('data-game-section') === selected);
        });
        gradedFieldset.style.display = GRADED_TYPES.indexOf(selected) !== -1 ? '' : 'none';
        timerField.style.display = TIMER_TYPES.indexOf(selected) !== -1 ? '' : 'none';
    }
    gameTypeSelect.addEventListener('change', updateVisibleSection);
    updateVisibleSection();

    function collectRows(key) {
        var container = containerFor(key);
        return Array.prototype.map.call(container.querySelectorAll('[data-row]'), function (rowEl) {
            var values = {};
            Array.prototype.forEach.call(rowEl.querySelectorAll('[data-field]'), function (input) {
                var field = input.getAttribute('data-field');
                if (field === 'answers' || field === 'distractors') {
                    values[field] = input.value.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
                } else {
                    values[field] = input.value;
                }
            });
            var existingId = rowEl.getAttribute('data-existing-id');
            if (existingId) {
                if (key === 'cards') { values.card_id = existingId; }
                if (key === 'sequence_items') { values.item_id = existingId; }
                if (key === 'memory_pairs') { values.pair_id = existingId; }
            }
            return values;
        });
    }

    function collectWords() {
        var container = containerFor('wordsearch_words');
        return Array.prototype.map.call(container.querySelectorAll('[data-field="word"]'), function (input) {
            return input.value.trim();
        }).filter(Boolean);
    }

    function setStatus(message, isError) {
        statusEl.textContent = message;
        statusEl.className = 'gx-studio-status' + (isError ? ' gx-error' : '');
    }

    $('#gx-studio-save', element).on('click', function () {
        var payload = {
            game_type: gameTypeSelect.value,
            display_name: $('#gx-studio-display-name', element).val(),
            instructions: $('#gx-studio-instructions', element).val(),
            is_shuffled: $('#gx-studio-is-shuffled', element).is(':checked'),
            timer_enabled: $('#gx-studio-timer-enabled', element).is(':checked'),
            weight: parseFloat($('#gx-studio-weight', element).val()) || 0,
            max_attempts: parseInt($('#gx-studio-max-attempts', element).val(), 10) || 0,
            cards: collectRows('cards'),
            sequence_items: collectRows('sequence_items'),
            cloze_text: $('#gx-studio-cloze-text', element).val(),
            cloze_blanks: collectRows('cloze_blanks'),
            wordsearch_words: collectWords(),
            memory_pairs: collectRows('memory_pairs'),
        };

        setStatus('Saving...', false);
        $.ajax({
            type: 'POST',
            url: saveUrl,
            data: JSON.stringify(payload),
            contentType: 'application/json',
            dataType: 'json',
            success: function (response) {
                if (response.success) {
                    setStatus('Saved.', false);
                    if (runtime.notify) { runtime.notify('save', { state: 'end' }); }
                } else {
                    setStatus(response.error || 'Save failed.', true);
                }
            },
            error: function () { setStatus('Save failed. Please try again.', true); },
        });
    });

    // Studio's generic "Save" button (outside this fragment, part of the
    // XBlock editor modal chrome) also triggers a save via runtime.notify;
    // support that path by exposing a save function the modal can call.
    element.gxSave = function () { $('#gx-studio-save', element).trigger('click'); };
}
