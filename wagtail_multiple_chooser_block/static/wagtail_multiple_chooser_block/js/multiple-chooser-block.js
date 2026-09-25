/**
 * The client-side implementation of MultipleChooserBlock: a ListBlock whose
 * "+" buttons open the chooser in multiple selection mode and add one item per
 * chosen object, as MultipleChooserPanel does for inline models.
 */
(() => {
  const { ListBlock, ListBlockDefinition } = window.wagtailStreamField.blocks;

  const CHECKBOX = '[data-multiple-choice-select]';
  const SUBMIT_BUTTON = '[data-multiple-choice-submit]';
  const FORM = 'form[data-multiple-choice-form]';

  /**
   * The title of a chooser item. Wagtail's choosers label each checkbox with
   * it: a <label for> in tables, and a surrounding <label> for images.
   */
  const getTitle = (checkbox) => {
    const label = [...checkbox.labels].find(({ textContent }) =>
      textContent.trim(),
    );
    return label ? label.textContent.trim() : checkbox.value;
  };

  let selectionCount = 0;

  /**
   * The selection in a chooser opened by a MultipleChooserBlock.
   *
   * The chooser replaces its results when searching or paginating, which loses
   * the selected checkboxes. This keeps the selection, selects it again in new
   * results, submits the selected items that aren't shown, and lists them all
   * above the confirm button. It also prevents selecting more items than the
   * list has room for, and items the list can't have twice.
   */
  class ChooserSelection {
    constructor(modal, { limit, unavailableIds, strings }) {
      this.modal = modal;
      this.limit = limit;
      this.unavailableIds = unavailableIds;
      this.strings = strings;
      /** The selected items, as a map of id to title */
      this.selected = new Map();

      selectionCount += 1;
      this.idPrefix = `multiple-chooser-block-selection-${selectionCount}`;
      this.list = document.createElement('ul');
      this.list.className = 'multiple-chooser-block-selection';

      modal.addEventListener('change', (event) => {
        if (event.target.matches(CHECKBOX)) this.onCheckboxChange(event.target);
      });
      // In the capture phase, so it runs before the modal submits the form
      modal.addEventListener('submit', (event) => this.submit(event.target), {
        capture: true,
      });
      // Runs when the results are replaced, but not for changes to the list
      new MutationObserver((mutations) => {
        if (mutations.some(({ target }) => !this.list.contains(target))) {
          this.update();
        }
      }).observe(modal, { childList: true, subtree: true });
    }

    get checkboxes() {
      return [...this.modal.querySelectorAll(CHECKBOX)];
    }

    onCheckboxChange(checkbox) {
      if (checkbox.checked) {
        this.selected.set(checkbox.value, getTitle(checkbox));
      } else {
        this.selected.delete(checkbox.value);
      }
      this.render();
    }

    deselect(id) {
      this.selected.delete(id);
      this.render();
    }

    /** Update the checkboxes and confirm button to match the selection. */
    update() {
      const isFull = this.selected.size >= this.limit;
      this.checkboxes.forEach((checkbox) => {
        const isSelected = this.selected.has(checkbox.value);
        checkbox.checked = isSelected;
        // Only enable checkboxes disabled here, not the ones the chooser disables
        if (
          this.unavailableIds.has(checkbox.value) ||
          (isFull && !isSelected)
        ) {
          if (!checkbox.disabled) {
            checkbox.disabled = true;
            checkbox.dataset.multipleChooserBlockDisabled = '';
          }
        } else if ('multipleChooserBlockDisabled' in checkbox.dataset) {
          checkbox.disabled = false;
          delete checkbox.dataset.multipleChooserBlockDisabled;
        }
      });

      const submitButton = this.modal.querySelector(SUBMIT_BUTTON);
      if (submitButton) {
        submitButton.disabled = !this.selected.size;
        if (!this.list.isConnected) submitButton.before(this.list);
      }
    }

    /** Update the list of selected items, and everything else with it. */
    render() {
      this.list.replaceChildren(
        ...[...this.selected].map(([id, title]) => {
          const item = document.createElement('li');
          item.className = 'multiple-chooser-block-selection__item';

          const titleElement = document.createElement('span');
          titleElement.id = `${this.idPrefix}-${id}`;
          titleElement.textContent = title;

          // Described by the title, so screen readers say what it clears
          const removeButton = document.createElement('button');
          removeButton.type = 'button';
          removeButton.className = 'multiple-chooser-block-selection__remove';
          removeButton.setAttribute('aria-label', this.strings.CLEAR);
          removeButton.setAttribute('aria-describedby', titleElement.id);
          removeButton.innerHTML =
            '<svg class="icon icon-cross" aria-hidden="true"><use href="#icon-cross"></use></svg>';
          removeButton.addEventListener('click', () => this.deselect(id));

          item.append(titleElement, removeButton);
          return item;
        }),
      );
      this.update();
    }

    /** Add the selected items that aren't shown to the submitted form. */
    submit(form) {
      if (!form.matches(FORM)) return;
      const shownIds = new Set(this.checkboxes.map(({ value }) => value));
      [...this.selected.keys()]
        .filter((id) => !shownIds.has(id))
        .forEach((id) => {
          const input = document.createElement('input');
          input.type = 'hidden';
          input.name = 'id';
          input.value = id;
          form.append(input);
        });
    }
  }

  class MultipleChooserBlock extends ListBlock {
    /** The bound chooser widget of a list item. */
    getChooserWidget(child) {
      const { chooserFieldName } = this.blockDef.meta;
      const block = chooserFieldName
        ? child.block.childBlocks[chooserFieldName]
        : child.block;
      return block.widget;
    }

    getChosenIds() {
      return new Set(
        this.children.map((child) =>
          String(this.getChooserWidget(child).getValue()),
        ),
      );
    }

    /** The number of items that can still be added, as limited by max_num. */
    get remaining() {
      const { maxNum } = this.blockDef.meta;
      return typeof maxNum === 'number'
        ? maxNum - this.children.length
        : Infinity;
    }

    /**
     * Called by the "+" buttons. Instead of adding an empty item, open the
     * chooser and add an item for each chosen object.
     */
    _onRequestInsert(index) {
      const { allowDuplicates, strings } = this.blockDef.meta;
      const openModals = new Set(document.querySelectorAll('.modal'));

      this.blockDef.chooserWidgetFactory.openModal(
        (result) => this.insertChosen(result, index),
        { multiple: true },
      );

      // The modal workflow adds the modal to the page straight away
      const modal = [...document.querySelectorAll('.modal')].find(
        (element) => !openModals.has(element),
      );
      if (modal) {
        new ChooserSelection(modal, {
          limit: this.remaining,
          unavailableIds: allowDuplicates ? new Set() : this.getChosenIds(),
          strings,
        });
      }
    }

    /** Add an item for each chosen object, starting at the given index. */
    insertChosen(result, index) {
      const { allowDuplicates } = this.blockDef.meta;
      const chosenIds = this.getChosenIds();
      let position = index;

      result.forEach((data) => {
        const id = String(data.id);
        if (this.remaining <= 0 || (!allowDuplicates && chosenIds.has(id))) {
          return;
        }
        chosenIds.add(id);
        const [, initialState, blockId] = this._getChildDataForInsertion();
        const child = this.insert(initialState, position, {
          id: blockId,
          animate: true,
        });
        this.getChooserWidget(child).setStateFromModalData(data);
        position += 1;
      });
    }

    /**
     * Disable the "+" buttons once max_num is reached, as MultipleChooserPanel
     * does with its button.
     */
    blockCountChanged() {
      super.blockCountChanged();
      const isFull = this.remaining <= 0;
      this.inserters.forEach((inserter) => {
        // The data-force-disabled attribute stops the modal workflow from
        // enabling the button again when the modal closes.
        if (isFull) {
          inserter.disable();
          inserter.element.setAttribute('data-force-disabled', 'true');
        } else {
          inserter.element.removeAttribute('data-force-disabled');
          inserter.enable();
        }
      });
    }
  }

  class MultipleChooserBlockDefinition extends ListBlockDefinition {
    /** The chooser widget definition, used to open the chooser. */
    get chooserWidgetFactory() {
      const { chooserFieldName } = this.meta;
      const chooserBlockDef = chooserFieldName
        ? this.childBlockDef.childBlockDefs.find(
            (childBlockDef) => childBlockDef.name === chooserFieldName,
          )
        : this.childBlockDef;
      return chooserBlockDef.widget;
    }

    render(placeholder, prefix, initialState, initialError) {
      return new MultipleChooserBlock(
        this,
        placeholder,
        prefix,
        initialState,
        initialError,
      );
    }
  }

  window.telepath.register(
    'wagtail_multiple_chooser_block.blocks.MultipleChooserBlock',
    MultipleChooserBlockDefinition,
  );
})();
