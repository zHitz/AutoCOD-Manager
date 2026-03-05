import { Result } from '../../../shared/result/Result.js';
import { WorkflowRunPolicy } from '../../../domain/workflow/policies/WorkflowRunPolicy.js';

export class RunWorkflowService {
    constructor({ executionRepo }) {
        this.executionRepo = executionRepo;
    }

    async execute(command) {
        try {
            // 1. Validate domain rules
            WorkflowRunPolicy.validate(command);

            const payload = {
                emulator_index: command.emulatorIndex,
                steps: command.steps,
                name: command.name || 'Manual Workflow'
            };

            // 2. Execute via repo
            const result = await this.executionRepo.run(payload);

            if (!result.ok) {
                return Result.fail(result.error);
            }

            return Result.ok(result.data);

        } catch (error) {
            return Result.fail(error);
        }
    }
}
