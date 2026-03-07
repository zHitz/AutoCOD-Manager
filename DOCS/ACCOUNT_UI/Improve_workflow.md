# Workflow Page — Kiến trúc tái thiết kế (4-layer)

## 1) Phân tích vấn đề kiến trúc hiện tại

Dựa trên `frontend/js/pages/workflow.js`, hiện trạng đang có các code smell lớn:

- **UI trộn logic nghiệp vụ + orchestration + data access** trong cùng object `WF3`.
  - `WF3` vừa render HTML, vừa xử lý state, vừa gọi API/LocalStorage, vừa xử lý luồng chạy bot/workflow.
- **Tight coupling rất cao với DOM + global state**.
  - Inline handlers (`onclick="WF3.*"`) gắn cứng vào implementation chi tiết, khó thay thế/test từng phần.
- **SRP violation (Single Responsibility Principle)**.
  - Một module làm quá nhiều nhiệm vụ: render view, validate input, build payload, gọi API, parse group/account, map emulator, persist cấu hình, log UI.
- **Dependency direction sai**.
  - “Page layer” đang phụ thuộc trực tiếp vào hạ tầng (`fetch`, `localStorage`) thay vì đi qua service/repository.
- **Cross-call module không qua application boundary**.
  - UI gọi trực tiếp nhiều endpoint và storage key khác nhau ở nhiều hàm khác nhau, gây hiệu ứng “sửa 1 chỗ vỡ nhiều chỗ”.
- **Khó test**.
  - Logic quan trọng phụ thuộc trực tiếp `document`, `window`, `fetch`, `localStorage`, khiến unit test gần như phải mock cả browser.

### Bằng chứng trong code hiện tại

- Inline event binding trực tiếp vào `WF3` từ template HTML (`onclick="WF3.*"`).
- UI layer gọi API trực tiếp trong `fetchFunctions`, `fetchTemplates`, `fetchRecipes`, `fetchEmulators`, `loadAccountsData`, `runBotActivities`, `saveRecipe`, `runWorkflow`.
- UI layer thao tác trực tiếp `localStorage` trong `getActivityConfig`, `saveActivityConfig`, `getPerActivityConfig`, `savePerActivityConfig`.
- Cùng một object vừa render và vừa xử lý orchestration lớn (`runBotActivities` vừa resolve group/account/emulator, vừa gọi API, vừa ghi log UI).

## 2) Redesign theo kiến trúc chuẩn 4 layer

## Mục tiêu

- **UI/Page Layer**: chỉ nhận event + gọi service + render state.
- **Application/Service Layer**: điều phối use-case (orchestrator).
- **Domain Layer**: chứa business rule thuần (pure logic), không biết UI/DB/API.
- **Infrastructure/Repository Layer**: implement truy cập API/DB/localStorage.

## Quy tắc dependency 1 chiều

```text
UI/Page  -->  Application/Service  -->  Domain
                                  \-->  Repository Interface --> Repository Impl --> DB/API/Storage
```

- UI **không được** gọi DB/API/localStorage trực tiếp.
- Domain **không phụ thuộc** UI hoặc chi tiết repository impl.
- Service phụ thuộc vào **interface** repository, không phụ thuộc concrete low-level detail.

## 3) Flow logic (text diagram)

### A. Save Recipe

```text
[UI] onClickSave
  -> [Service] SaveRecipeService.execute(command)
    -> [Domain] RecipeFactory.create(...) + RecipePolicy.validate(...)
      -> [Repository Interface] WorkflowRepository.saveRecipe(recipe)
        -> [Repository Impl] HttpWorkflowRepository.POST /api/workflow/recipes
          -> [DB/API]
    <- result DTO
  <- update state + render toast
```

### B. Run Workflow

```text
[UI] onClickRun
  -> [Service] RunWorkflowService.execute(command)
    -> [Domain] WorkflowRunPolicy.validateSteps(...)
    -> [Repository Interface] EmulatorRepository.getOnline()
      -> [Repository Impl] HttpEmulatorRepository.GET /api/emulators/all
        -> [DB/API]
    -> [Repository Interface] WorkflowExecutionRepository.run(...)
      -> [Repository Impl] HttpWorkflowExecutionRepository.POST /api/workflow/run
        -> [DB/API]
  <- execution accepted/rejected
  <- render status/log
```

### C. Run Bot Activities

```text
[UI] onClickStartBot
  -> [Service] RunBotActivitiesService.execute(groupId)
    -> [Repository Interface] GroupRepository.getById(groupId)
    -> [Repository Interface] AccountRepository.getByIds(accountIds)
    -> [Domain] ActivitySelectionPolicy.pickEnabled(config)
    -> [Domain] EmulatorResolutionPolicy.resolve(accounts)
    -> [Repository Interface] BotRepository.start(payload)
      -> [Repository Impl] HttpBotRepository.POST /api/bot/run
        -> [DB/API]
  <- result
  <- render log/toast
```

## 4) Cấu trúc folder đề xuất

```text
frontend/js/
  pages/
    workflow/
      WorkflowPage.js                # UI only
      WorkflowViewModel.js           # UI state mapping (optional)
      WorkflowEventBinder.js         # bind DOM events -> handlers

  application/
    workflow/
      services/
        LoadWorkflowScreenService.js
        SaveRecipeService.js
        RunWorkflowService.js
        RunBotActivitiesService.js
      dto/
        SaveRecipeCommand.js
        RunWorkflowCommand.js
        RunBotActivitiesCommand.js

  domain/
    workflow/
      entities/
        Recipe.js
        WorkflowStep.js
        ActivityConfig.js
      policies/
        RecipePolicy.js
        WorkflowRunPolicy.js
        ActivitySelectionPolicy.js
        EmulatorResolutionPolicy.js
      errors/
        DomainError.js

  infrastructure/
    workflow/
      repositories/
        HttpWorkflowRepository.js
        HttpExecutionRepository.js
        HttpBotRepository.js
        HttpGroupRepository.js
        HttpAccountRepository.js
        LocalActivityConfigRepository.js
      api/
        WorkflowApiClient.js

  shared/
    http/HttpClient.js
    eventbus/EventBus.js
    result/Result.js
```

## 5) Pseudo-code theo từng layer

### 5.1 UI handler (Page Layer)

```javascript
// pages/workflow/WorkflowPage.js
class WorkflowPage {
  constructor({ loadService, saveService, runService, runBotService }) {
    this.loadService = loadService;
    this.saveService = saveService;
    this.runService = runService;
    this.runBotService = runBotService;
    this.state = { recipes: [], steps: [], selectedEmulator: null };
  }

  async onInit() {
    const vm = await this.loadService.execute();
    this.state = { ...this.state, ...vm };
    this.render();
  }

  async onSaveClick() {
    const cmd = {
      recipeId: this.state.currentRecipeId,
      name: this.readRecipeNameInput(),
      steps: this.state.steps,
    };

    const result = await this.saveService.execute(cmd);
    if (result.ok) this.showToast('Saved');
    else this.showError(result.error.message);
  }

  async onRunClick() {
    const cmd = {
      emulatorIndex: this.state.selectedEmulator,
      steps: this.state.steps,
    };

    const result = await this.runService.execute(cmd);
    this.renderRunStatus(result);
  }
}
```

### 5.2 Service layer (Application)

```javascript
// application/workflow/services/SaveRecipeService.js
class SaveRecipeService {
  constructor({ workflowRepo, recipePolicy }) {
    this.workflowRepo = workflowRepo;        // interface
    this.recipePolicy = recipePolicy;        // domain policy
  }

  async execute(cmd) {
    const recipe = Recipe.create({
      id: cmd.recipeId,
      name: cmd.name,
      steps: cmd.steps,
    });

    this.recipePolicy.validate(recipe);

    const saved = await this.workflowRepo.saveRecipe(recipe);
    return Result.ok({ id: saved.id, action: saved.action });
  }
}
```

### 5.3 Domain logic

```javascript
// domain/workflow/policies/WorkflowRunPolicy.js
class WorkflowRunPolicy {
  validate(command) {
    if (!command.emulatorIndex) throw new DomainError('EMULATOR_REQUIRED');
    if (!Array.isArray(command.steps) || command.steps.length === 0) {
      throw new DomainError('STEPS_REQUIRED');
    }

    for (const step of command.steps) {
      if (!step.functionId) throw new DomainError('INVALID_STEP');
    }
  }
}
```

### 5.4 Repository interface

```javascript
// application/workflow/ports/WorkflowRepository.js
export class WorkflowRepository {
  async getFunctions() { throw new Error('Not implemented'); }
  async getTemplates() { throw new Error('Not implemented'); }
  async getRecipes() { throw new Error('Not implemented'); }
  async saveRecipe(recipe) { throw new Error('Not implemented'); }
}
```

### 5.5 Repository implementation

```javascript
// infrastructure/workflow/repositories/HttpWorkflowRepository.js
export class HttpWorkflowRepositoryImpl extends WorkflowRepository {
  constructor({ httpClient }) {
    super();
    this.http = httpClient;
  }

  async getRecipes() {
    return this.http.get('/api/workflow/recipes');
  }

  async saveRecipe(recipe) {
    return this.http.post('/api/workflow/recipes', {
      id: recipe.id,
      name: recipe.name,
      steps: recipe.steps,
      icon: recipe.icon,
      description: recipe.description,
    });
  }
}
```

## 6) Vì sao kiến trúc mới tốt hơn

- **Dễ test hơn**
  - Domain policy/entity là pure function/pure object → test unit không cần DOM/fetch.
  - Service test bằng mock repository interface.
  - UI test tập trung vào event/render, không phải test business rule phức tạp.

- **Dễ maintain hơn**
  - Mỗi layer có trách nhiệm rõ ràng, sửa logic nghiệp vụ không phải đụng HTML rendering.
  - Endpoint/API thay đổi chỉ cần sửa repository implementation.

- **Dễ scale hơn**
  - Thêm use-case mới bằng cách thêm service/domain policy mới, không làm phình object `WF3`.
  - Có thể chuyển `fetch` sang websocket/API client khác mà không ảnh hưởng domain.

- **Không còn call chéo tùm lum**
  - Tất cả luồng bắt buộc đi qua service orchestrator.
  - UI chỉ “phát event” và “render result”; không tự ý gọi chéo module dữ liệu.

## 7) Kế hoạch migration thực tế (không sửa lặt vặt)

1. **Đóng băng tính năng** trên Workflow page trong nhánh migration.
2. Tạo mới module 4 layer song song với `WF3` (strangler pattern).
3. Migrating theo use-case lớn:
   - Load screen
   - Save recipe
   - Run workflow
   - Run bot activities
4. Mỗi use-case chuyển xong thì ngắt đường gọi trực tiếp `fetch/localStorage` khỏi UI.
5. Khi 100% use-case đã qua service layer, loại bỏ `WF3` monolith.


## 8) Bổ sung bắt buộc để tái sử dụng cho Page Task (ghi lại đầy đủ thông tin)

Bạn nói rất đúng: nếu muốn dùng lại cho **Page Task**, chỉ có tách layer là chưa đủ. Cần thêm chuẩn **ghi nhận dữ liệu đầy đủ** theo hướng domain-first + auditability.

### 8.1 Các loại dữ liệu cần ghi

- **Execution Metadata** (cấp phiên chạy)
  - `run_id` (UUID)
  - `source_page` (`workflow` | `task`)
  - `trigger_type` (`manual` | `schedule` | `retry`)
  - `triggered_by` (user/system)
  - `group_id`, `recipe_id` / `task_id`
  - `emulator_indices`
  - `start_at`, `end_at`, `duration_ms`
  - `final_status` (`SUCCESS` | `FAILED` | `CANCELLED`)

- **Step Execution Log** (cấp từng bước)
  - `run_id`, `step_index`, `function_id`
  - `input_snapshot` (sanitized)
  - `output_snapshot` (sanitized)
  - `attempt`, `retry_count`
  - `step_status`
  - `started_at`, `ended_at`, `latency_ms`
  - `error_code`, `error_message` (nếu fail)

- **Domain Events** (dành cho analytics/debug)
  - `event_id`, `run_id`, `event_type`
  - `payload_json`
  - `created_at`

- **Audit Trail** (mức người dùng/cấu hình)
  - ai đổi config, đổi lúc nào, giá trị cũ/mới
  - lý do thay đổi (optional)

### 8.2 Quy tắc phân tầng khi ghi log

- UI chỉ gọi service: `taskExecutionService.start(...)`, `taskExecutionService.saveConfig(...)`.
- Service quyết định **khi nào** ghi execution log/audit log.
- Domain phát sinh event nghiệp vụ (`TaskStarted`, `StepFailed`, `TaskCompleted`).
- Repository chịu trách nhiệm persist vào DB/API.
- Không cho phép UI gọi trực tiếp storage/log endpoint.

### 8.3 Chuẩn hóa model dùng chung cho Workflow + Task

```text
ExecutionAggregate
  - runId
  - sourcePage
  - actor
  - target (group/task/recipe)
  - steps[]
  - status
  - timestamps

StepExecution
  - index
  - functionId
  - input
  - output
  - status
  - error
```

=> Page Workflow và Page Task chỉ khác **entry command**; phần execution core + logging nên dùng chung.

### 8.4 Repository contracts nên bổ sung

```javascript
// application/task/ports/ExecutionLogRepository.js
export class ExecutionLogRepository {
  async createRun(meta) { throw new Error('Not implemented'); }
  async appendStepLog(runId, stepLog) { throw new Error('Not implemented'); }
  async completeRun(runId, summary) { throw new Error('Not implemented'); }
}

// application/task/ports/AuditRepository.js
export class AuditRepository {
  async logConfigChange(entry) { throw new Error('Not implemented'); }
}
```

### 8.5 Pseudo-flow cho Task page (có ghi log đầy đủ)

```text
[UI Task] click Start Task
  -> [TaskService] startTask(command)
    -> [Domain] validateTaskCommand(command)
    -> [ExecutionLogRepo] createRun(meta)
    -> loop step in task
         -> [Domain] validateStep(step)
         -> [TaskExecutorRepo] executeStep(step)
         -> [ExecutionLogRepo] appendStepLog(runId, stepResult)
    -> [ExecutionLogRepo] completeRun(runId, summary)
  <- result DTO (runId, status, stats)
[UI Task] render + poll/get detail by runId
```

### 8.6 API/DB đề xuất tối thiểu để “đủ thông tin”

- `task_runs`
  - `run_id`, `source_page`, `trigger_type`, `triggered_by`, `target_id`, `status`, `start_at`, `end_at`, `duration_ms`, `metadata_json`
- `task_run_steps`
  - `id`, `run_id`, `step_index`, `function_id`, `input_json`, `output_json`, `status`, `error_code`, `error_message`, `started_at`, `ended_at`, `latency_ms`
- `audit_logs`
  - `id`, `actor`, `action`, `target_type`, `target_id`, `before_json`, `after_json`, `reason`, `created_at`

### 8.7 Checklist để triển khai thực tế (khuyến nghị làm ngay)

1. Tạo `ExecutionLogRepository` + `AuditRepository` ports ở application layer.
2. Implement hạ tầng HTTP/DB cho 2 repository này.
3. Chuẩn hóa `run_id` và propagate xuyên suốt service/domain/repository.
4. Định nghĩa chuẩn sanitize dữ liệu nhạy cảm trước khi ghi `input/output`.
5. Bổ sung endpoint query lịch sử theo `run_id`, `group_id`, `task_id`, `date range`.
6. Thêm test:
   - service test: có gọi createRun/appendStepLog/completeRun đúng thứ tự.
   - failure test: step fail vẫn ghi log + completeRun với FAILED.
   - contract test cho repository payload.

### 8.8 Kết luận cập nhật

Có, **cần làm thêm**: bổ sung trục **Execution Logging + Audit Trail** như một phần chính thức của kiến trúc 4-layer. Nếu không có phần này, Page Task sẽ thiếu khả năng truy vết, debug production, và báo cáo vận hành.
