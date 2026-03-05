import { Result } from '../../../shared/result/Result.js';

export class LoadWorkflowScreenService {
    constructor({ workflowRepo, emuRepo, groupRepo, accountRepo, configRepo }) {
        this.workflowRepo = workflowRepo;
        this.emuRepo = emuRepo;
        this.groupRepo = groupRepo;
        this.accountRepo = accountRepo;
        this.configRepo = configRepo;
    }

    async execute() {
        try {
            // Load base UI data in parallel
            const [
                functionsResult,
                templatesResult,
                recipesResult,
                emulatorsResult,
                registryResult,
                groupsResult,
                accountsResult
            ] = await Promise.all([
                this.workflowRepo.getFunctions(),
                this.workflowRepo.getTemplates(),
                this.workflowRepo.getRecipes(),
                this.emuRepo.getAll(),
                this.configRepo.getRegistry(),
                this.groupRepo.getAll(),
                this.accountRepo.getAll()
            ]);

            // Gather any errors to report up
            const errors = [];
            if (!functionsResult.ok) errors.push(functionsResult.error.message);
            if (!templatesResult.ok) errors.push(templatesResult.error.message);
            if (!recipesResult.ok) errors.push(recipesResult.error.message);
            // Emulators are okay to fail if offline

            if (errors.length > 0) {
                return Result.fail(new Error(`Failed to load screen data: \n${errors.join('\n')}`));
            }

            return Result.ok({
                functions: functionsResult.data,
                templates: templatesResult.data,
                recipes: recipesResult.data,
                emulators: emulatorsResult.ok ? emulatorsResult.data : [],
                systemActivities: registryResult.ok ? registryResult.data : [],
                groups: groupsResult.ok ? groupsResult.data : [],
                accounts: accountsResult.ok ? accountsResult.data : []
            });
        } catch (error) {
            return Result.fail(error);
        }
    }
}
