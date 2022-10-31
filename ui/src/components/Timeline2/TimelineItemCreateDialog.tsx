import { FC } from 'react';
import { Button, Dialog, Intent, Classes } from '@blueprintjs/core';
import { Model, Schema, Entity } from '@alephdata/followthemoney';
import TimelineItemCreateForm from './TimelineItemCreateForm';

type TimelineItemCreateDialogProps = Dialog['props'] & {
  model: Model;
  onCreate: (entity: Entity) => void;
  fetchEntitySuggestions?: (
    schema: Schema,
    query: string
  ) => Promise<Array<Entity>>;
};

const TimelineItemCreateDialog: FC<TimelineItemCreateDialogProps> = ({
  model,
  isOpen,
  onClose,
  onCreate,
  fetchEntitySuggestions,
}) => {
  return (
    <Dialog
      title="Add new item to timeline"
      usePortal={true}
      isOpen={isOpen}
      onClose={onClose}
    >
      <div className={Classes.DIALOG_BODY}>
        <TimelineItemCreateForm
          id="timeline-item-create-form"
          model={model}
          onSubmit={onCreate}
          fetchEntitySuggestions={fetchEntitySuggestions}
        />
      </div>
      <div className={Classes.DIALOG_FOOTER}>
        <div className={Classes.DIALOG_FOOTER_ACTIONS}>
          <Button
            type="submit"
            text="Add"
            form="timeline-item-create-form"
            intent={Intent.PRIMARY}
          />
        </div>
      </div>
    </Dialog>
  );
};

export default TimelineItemCreateDialog;