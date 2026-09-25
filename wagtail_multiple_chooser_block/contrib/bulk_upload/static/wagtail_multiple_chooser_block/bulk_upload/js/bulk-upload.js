/**
 * Adds the items uploaded with Wagtail's bulk upload in the chooser. When all
 * uploads succeed, they are added straight away, as with the chooser's upload
 * form for a single item. Otherwise, the chooser stays open with the status of
 * each upload, and its confirm button adds the uploaded items. The rows stay
 * in the list, so it's clear what's been uploaded.
 */
$(() => {
  const form = document.querySelector(
    '[data-multiple-chooser-block-bulk-upload]',
  );
  const list = document.getElementById('upload-list');
  /** The inputs with the ids of the uploaded items, by their row in the list */
  const inputs = new Map();
  let pending = 0;
  let needsAttention = false;

  const choose = (row, id) => {
    if (!inputs.has(row)) {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'id';
      form.append(input);
      inputs.set(row, input);
    }
    inputs.get(row).value = id;
  };

  /** Show the message for the item that a row adds, in place of its form. */
  const showMessage = (row, message) => {
    const paragraph = document.createElement('p');
    paragraph.className = 'status-msg success';
    paragraph.textContent = message;
    row.querySelector('.right').append(paragraph);
  };

  const finish = () => {
    pending -= 1;
    if (pending > 0) return;
    if (needsAttention) {
      form.hidden = false;
    } else if (inputs.size) {
      form.requestSubmit();
    }
  };

  // Wagtail's bulk upload uses jQuery File Upload, which triggers these events
  // for each file. Uploads are sequential, so wait until none are left.
  $('#fileupload')
    .on('fileuploadadd', () => {
      pending += 1;
    })
    .on('fileuploaddone', (event, data) => {
      const row = data.context[0];
      const response = JSON.parse(data.result);
      const id = response.image_id ?? response.doc_id;
      if (id) choose(row, id);
      if (response.message) showMessage(row, response.message);
      // Failed, a duplicate, or needs its form filled in to become an item
      if (!id || response.duplicate) needsAttention = true;
      finish();
    })
    .on('fileuploadfail fileuploadprocessfail', () => {
      needsAttention = true;
      finish();
    });

  // A duplicate image: the choice of Wagtail's image chooser, after which the
  // row shows the image that's used
  $(list).on('click', '[data-multiple-chooser-block-use-new]', (event) => {
    const button = event.currentTarget;
    const row = button.closest('#upload-list > li');
    button.closest('[data-multiple-chooser-block-duplicate]').remove();
    row.classList.replace('upload-duplicate', 'upload-success');
    showMessage(row, button.dataset.message);
  });
  $(list).on(
    'click',
    '[data-multiple-chooser-block-use-existing]',
    async (event) => {
      const button = event.currentTarget;
      const row = button.closest('#upload-list > li');
      const duplicate = button.closest(
        '[data-multiple-chooser-block-duplicate]',
      );
      const buttons = duplicate.querySelectorAll('button');
      buttons.forEach((element) => {
        element.disabled = true;
      });
      const response = await fetch(button.dataset.deleteUrl, {
        method: 'POST',
        body: new FormData(duplicate.querySelector('form')),
      });
      if (!response.ok) {
        buttons.forEach((element) => {
          element.disabled = false;
        });
        return;
      }
      choose(row, button.dataset.multipleChooserBlockUseExisting);
      // Show the existing image in the row, in place of the new one
      row
        .querySelector('.thumb')
        .replaceChildren(duplicate.querySelector('img'));
      row.querySelector('.left').lastChild.textContent =
        duplicate.querySelector('figcaption').textContent;
      duplicate.remove();
      row.classList.replace('upload-duplicate', 'upload-success');
      showMessage(row, button.dataset.message);
    },
  );

  // Wagtail removes a row once its form is saved, so save it here instead,
  // before the event reaches Wagtail's handler, and keep the row
  list.addEventListener(
    'submit',
    async (event) => {
      const itemForm = event.target;
      const row = itemForm.closest('#upload-list > li');
      event.preventDefault();
      event.stopPropagation();
      const response = await fetch(itemForm.action, {
        method: 'POST',
        body: new FormData(itemForm),
      });
      const data = await response.json();
      if (data.success) {
        choose(row, data.image_id ?? data.doc_id);
        showMessage(row, data.message);
        itemForm.remove();
      } else {
        itemForm.outerHTML = data.form;
      }
    },
    { capture: true },
  );
});
