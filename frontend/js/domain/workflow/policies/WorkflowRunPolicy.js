import { DomainError } from '../errors/DomainError.js';

export class WorkflowRunPolicy {
    static validate(command) {
        if (command.emulatorIndex === undefined || command.emulatorIndex === null) {
            throw new DomainError('EMULATOR_REQUIRED', 'Please select an emulator first.');
        }

        if (!Array.isArray(command.steps) || command.steps.length === 0) {
            throw new DomainError('NO_STEPS', 'No steps to run.');
        }

        for (const step of command.steps) {
            if (!step.function_id) {
                throw new DomainError('INVALID_STEP', 'One or more steps are missing a function_id');
            }
        }

        return true;
    }
}
