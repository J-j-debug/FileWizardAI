import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatCardModule } from '@angular/material/card';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { DataService } from '../data.service';
import { DeepSummaryDialogComponent } from './deep-summary-dialog.component';

@Component({
    selector: 'app-thesis-manager',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MatButtonModule,
        MatInputModule,
        MatFormFieldModule,
        MatIconModule,
        MatDialogModule,
        MatCardModule,
        MatExpansionModule,
        MatProgressSpinnerModule,
        MatTabsModule,
        MatChipsModule,
        MatTooltipModule,
        DeepSummaryDialogComponent
    ],
    template: `
    <div class="thesis-container">
      <!-- Project Selection / Creation -->
      <div class="project-header" *ngIf="!activeProject">
        <h2>Thesis Projects</h2>
        <div class="create-project-form">
            <mat-form-field appearance="outline">
                <mat-label>Project Name</mat-label>
                <input matInput [(ngModel)]="newProjectName">
            </mat-form-field>
            <mat-form-field appearance="outline">
                <mat-label>Description</mat-label>
                <input matInput [(ngModel)]="newProjectDescription">
            </mat-form-field>
            <button mat-flat-button color="primary" (click)="createProject()" [disabled]="!newProjectName">
                Create Project
            </button>
        </div>
        
        <div class="project-list">
            <mat-card *ngFor="let p of projects" class="project-card" (click)="selectProject(p)">
                <mat-card-header>
                    <mat-card-title>{{p.name}}</mat-card-title>
                    <mat-card-subtitle>{{p.created_at | date}}</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                    <p>{{p.description}}</p>
                </mat-card-content>
            </mat-card>
        </div>
      </div>

      <!-- Active Project View -->
      <div class="active-project" *ngIf="activeProject">
        <button mat-button (click)="activeProject = null">
            <mat-icon>arrow_back</mat-icon> Back to Projects
        </button>
        
        <div class="split-view">
            <!-- Left Panel: Plan Input -->
            <div class="panel plan-panel">
                <h3>Thesis Plan</h3>
                <p class="hint">Define your chapters and what you are looking for.</p>
                
                <div class="chapters-list">
                    <div *ngFor="let chapter of chapters; let i = index" class="chapter-input-item">
                        <div class="chapter-header">
                            <span class="chapter-num">Chapter {{i + 1}}</span>
                            <button mat-icon-button color="warn" (click)="removeChapter(i)">
                                <mat-icon>delete</mat-icon>
                            </button>
                        </div>
                        <mat-form-field appearance="outline" class="full-width">
                            <mat-label>Title</mat-label>
                            <input matInput [(ngModel)]="chapter.title" placeholder="e.g. Cognitive Biases">
                        </mat-form-field>
                        <mat-form-field appearance="outline" class="full-width">
                            <mat-label>Description / Keywords</mat-label>
                            <textarea matInput [(ngModel)]="chapter.description" rows="3" placeholder="What concepts should match this chapter?"></textarea>
                        </mat-form-field>
                    </div>
                </div>
                
                <div class="actions">
                    <button mat-button (click)="addChapter()">
                        <mat-icon>add</mat-icon> Add Chapter
                    </button>
                    <span class="spacer"></span>
                    <button mat-stroked-button color="primary" (click)="savePlan()" [disabled]="loading">
                        <mat-icon>save</mat-icon> Save Plan
                    </button>
                    <button mat-raised-button color="primary" (click)="generateStructure()" [disabled]="loading">
                        <mat-icon>search</mat-icon> Find Relevant Files
                    </button>
                </div>
            </div>

            <!-- Right Panel: Results -->
            <div class="panel results-panel">
                <h3>Proposed Structure</h3>
                <div *ngIf="!structure && !loading" class="empty-state">
                    Run "Find Relevant Files" to see suggestions.
                </div>
                
                <div *ngIf="loading" class="loading-state">
                    <mat-spinner diameter="40"></mat-spinner>
                    <p>Analyzing global relevance (Max-Pooling)...</p>
                </div>

                <div *ngIf="structure" class="structure-tree">
                    <mat-accordion>
                        <mat-expansion-panel *ngFor="let item of structure" [expanded]="true">
                            <mat-expansion-panel-header>
                                <mat-panel-title>
                                    <strong>{{item.chapter_title}}</strong>
                                </mat-panel-title>
                                <mat-panel-description>
                                    {{item.relevant_files.length}} relevant files
                                </mat-panel-description>
                            </mat-expansion-panel-header>
                            
                            <div class="file-list">
                                <div *ngFor="let file of item.relevant_files" class="file-item">
                                    <div class="file-header">
                                        <span class="filename">{{file.filename}}</span>
                                        <mat-chip-set>
                                            <mat-chip 
                                                [class.high-score]="file.score > 0.7"
                                                [class.med-score]="file.score > 0.4 && file.score <= 0.7"
                                                [matTooltip]="'Relevance Score (0-1). indicates semantic similarity to chapter.\\n> 0.7: Highly Relevant\\n0.4-0.7: Moderately Relevant'"
                                                matTooltipPosition="above"
                                            >
                                                Score: {{ file.score | number:'1.2-2' }}
                                            </mat-chip>
                                        </mat-chip-set>
                                    </div>
                                    <div class="file-excerpt">
                                        "{{file.excerpt | slice:0:150}}..."
                                    </div>
                                    <div class="file-actions">
                                        <button mat-button color="accent" (click)="openFile(file.metadata.file_path)">Open</button>
                                        <button mat-button (click)="viewDeepSummary(file.metadata.file_path)">Deep Summary</button>
                                    </div>
                                </div>
                            </div>
                        </mat-expansion-panel>
                    </mat-accordion>
                </div>
            </div>
        </div>
      </div>
    </div>
  `,
    styles: [`
    .thesis-container {
        padding: 1rem;
    }
    .project-header {
        max-width: 800px;
        margin: 0 auto;
    }
    .create-project-form {
        display: flex;
        gap: 1rem;
        align-items: center;
        margin-bottom: 2rem;
    }
    .project-card {
        margin-bottom: 1rem;
        cursor: pointer;
        transition: transform 0.2s;
        &:hover { transform: translateY(-2px); }
    }
    .active-project {
        animation: fadeIn 0.3s ease;
    }
    .split-view {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2rem;
        margin-top: 1rem;
    }
    .panel {
        background: var(--surface);
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid var(--border);
    }
    .chapter-input-item {
        background: rgba(0,0,0,0.02);
        padding: 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
        border-left: 3px solid var(--primary);
    }
    .chapter-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    .full-width {
        width: 100%;
        display: block;
    }
    .file-item {
        border-bottom: 1px solid var(--border);
        padding: 0.8rem 0;
        &:last-child { border-bottom: none; }
    }
    .file-header {
        display: flex;
        justify-content: space-between;
        font-weight: 500;
        margin-bottom: 0.2rem;
    }
    .high-score {
        color: var(--primary);
        font-weight: bold;
    }
    .file-excerpt {
        font-size: 0.85rem;
        color: var(--text-secondary);
        font-style: italic;
        margin-bottom: 0.5rem;
    }
    .file-actions {
        display: flex;
        gap: 0.5rem;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
  `]
})
export class ThesisManagerComponent implements OnInit {
    projects: any[] = [];
    activeProject: any = null;

    newProjectName = '';
    newProjectDescription = '';

    chapters: any[] = [{ title: '', description: '' }];
    structure: any = null;
    loading = false;

    constructor(private dataService: DataService, private dialog: MatDialog) { }

    ngOnInit() {
        this.loadProjects();
    }

    loadProjects() {
        this.dataService.getThesisProjects().subscribe(p => this.projects = p);
    }

    createProject() {
        this.dataService.createThesisProject({
            name: this.newProjectName,
            description: this.newProjectDescription
        }).subscribe(p => {
            this.projects.push(p);
            this.newProjectName = '';
            this.newProjectDescription = '';
            this.selectProject(p);
        });
    }

    selectProject(project: any) {
        this.activeProject = project;
        this.structure = null;
        this.chapters = [{ title: '', description: '' }]; // Reset default

        // Load Plan
        this.dataService.getThesisPlan(project.id).subscribe(plan => {
            if (plan && plan.length > 0) {
                this.chapters = plan;
            }
        });

        // Load Structure (if exists)
        this.dataService.getThesisStructure(project.id).subscribe(s => {
            if (s && s.length > 0) {
                this.structure = s;
                // If plan was empty but structure exists, maybe populate chapters from structure? 
                // But plan usually takes precedence or is the source.
            }
        });
    }

    addChapter() {
        this.chapters.push({ title: '', description: '' });
    }

    removeChapter(index: number) {
        this.chapters.splice(index, 1);
    }

    savePlan() {
        if (!this.activeProject) return;
        this.loading = true;
        this.dataService.saveThesisPlan(this.activeProject.id, this.chapters).subscribe({
            next: () => {
                this.loading = false;
                // Optional: Snackbar "Plan Saved"
            },
            error: (err) => {
                this.loading = false;
                alert("Error saving plan: " + err.message);
            }
        });
    }

    generateStructure() {
        this.loading = true;
        // Auto-save plan before generating
        this.dataService.saveThesisPlan(this.activeProject.id, this.chapters).subscribe();

        this.dataService.generateThesisStructure(this.activeProject.id, this.chapters)
            .subscribe({
                next: (res) => {
                    this.structure = res.structure;
                    this.loading = false;
                },
                error: (err) => {
                    console.error(err);
                    this.loading = false;
                    alert('Error generating structure: ' + err.message);
                }
            });
    }

    openFile(path: string) {
        this.dataService.openFile(path).subscribe();
    }

    viewDeepSummary(path: string) {
        this.dialog.open(DeepSummaryDialogComponent, {
            data: { filePath: path },
            width: '800px',
            maxHeight: '90vh'
        });
    }
}
