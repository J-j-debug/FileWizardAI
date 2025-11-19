import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

// Angular Material Modules
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { DataService } from '../data.service';
import { ResultsComponent } from './results.component';

interface ExtensionGroup {
  name: string;
  icon: string;
  extensions: string[];
  selected: number;
  total: number;
  expanded: boolean;
}

@Component({
  selector: 'app-deep-research',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatSelectModule,
    MatTooltipModule,
    ResultsComponent
  ],
  template: `
    <div class="deep-research-container">
      <div class="config-section">
        <div class="section-header">
          <div class="icon-title">
            <mat-icon>folder_open</mat-icon>
            <div>
              <h2>Configuration des Fichiers</h2>
              <p>Sélectionnez les fichiers à analyser.</p>
            </div>
          </div>
        </div>

        <div class="input-section">
          <mat-form-field appearance="outline" class="root-path-field">
            <mat-label>Root Path</mat-label>
            <input matInput [(ngModel)]="rootPath" (ngModelChange)="onPathChange($event)" placeholder="Sélectionnez un dossier">
            <mat-icon matSuffix>folder_open</mat-icon>
          </mat-form-field>
        </div>

        <div class="extensions-section">
          <div class="extensions-header">
            <h3>Extensions de Fichiers</h3>
            <div class="extension-actions">
              <button mat-button color="primary" (click)="selectAll()">
                <mat-icon>select_all</mat-icon>
                Tout Sélectionner
              </button>
              <button mat-button color="warn" (click)="clearAll()">
                <mat-icon>clear_all</mat-icon>
                Effacer
              </button>
            </div>
          </div>
          <div class="extension-groups">
            <div *ngFor="let group of extensionGroups" class="extension-group">
              <div class="group-header" (click)="toggleGroup(group)">
                <div class="group-info">
                  <mat-icon>{{group.icon}}</mat-icon>
                  <span>{{group.name}}</span>
                </div>
                <div class="group-count">
                  {{group.selected}}/{{group.total}}
                  <mat-icon class="expand-icon" [class.expanded]="group.expanded">expand_more</mat-icon>
                </div>
              </div>
              <div class="group-content" [class.expanded]="group.expanded">
                <mat-checkbox *ngFor="let ext of group.extensions"
                            [checked]="isExtensionSelected(ext)"
                            (change)="toggleExtension(ext, group)"
                            color="primary">
                  {{ext}}
                </mat-checkbox>
              </div>
            </div>
          </div>
        </div>
         <mat-checkbox [(ngModel)]="isRecursive" color="primary" class="subdirectories-check">
            Inclure les sous-dossiers
          </mat-checkbox>
      </div>
      <div class="analysis-section">
         <div class="section-header">
          <div class="icon-title">
            <mat-icon>science</mat-icon>
            <div>
              <h2>Schéma d'Analyse</h2>
              <p>Définissez les questions et les tags pour l'analyse.</p>
            </div>
          </div>
        </div>

        <mat-form-field appearance="outline" class="analysis-field">
          <mat-label>Instruction pour le Résumé</mat-label>
          <textarea matInput cdkTextareaAutosize cdkAutosizeMinRows="2" [(ngModel)]="summaryPrompt"></textarea>
        </mat-form-field>

        <div *ngFor="let q of complementaryQuestions; let i = index" class="question-block">
          <mat-form-field appearance="outline" class="analysis-field">
            <mat-label>Question Complémentaire {{ i + 1 }}</mat-label>
            <input matInput [(ngModel)]="q.question">
          </mat-form-field>
          <mat-checkbox [(ngModel)]="q.isYesNo" color="primary">Réponse Oui/Non</mat-checkbox>
        </div>

        <button mat-stroked-button (click)="addQuestion()">
          <mat-icon>add</mat-icon>
          Ajouter une question
        </button>

        <mat-form-field appearance="outline" class="analysis-field tags-field">
          <mat-label>Tags à appliquer (séparés par des virgules)</mat-label>
          <input matInput [(ngModel)]="tags" placeholder="ex: fiscalité, éco-taxe, droit social">
        </mat-form-field>

        <button mat-flat-button color="primary" class="analyze-btn" (click)="startAnalysis()">
          <mat-icon>pageview</mat-icon>
          Lancer l'Analyse
        </button>
      </div>
    </div>
    <div *ngIf="analysisResult" class="results-section">
      <app-results [results]="analysisResult.results"></app-results>
    </div>
  `,
  styles: [`
    .deep-research-container {
      display: grid;
      grid-template-columns: 1fr 1.5fr;
      gap: 2rem;
      margin-bottom: 2rem;
    }
    .results-section {
        grid-column: 1 / -1; /* Span full width */
    }
    .config-section, .analysis-section {
      background: var(--surface);
      border-radius: var(--radius-lg);
      padding: 2rem;
      border: 1px solid var(--border);
      height: fit-content;
    }
    .section-header { margin-bottom: 2rem; }
    .icon-title { display: flex; align-items: center; gap: 1rem; }
    .icon-title mat-icon { font-size: 2rem; width: 2rem; height: 2rem; color: var(--primary); }
    .icon-title h2 { margin: 0; font-size: 1.5rem; }
    .icon-title p { margin: 0.25rem 0 0 0; color: var(--text-secondary); font-size: 0.9rem; }
    .input-section { margin-bottom: 2rem; }
    .root-path-field { width: 100%; }
    .extensions-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .extension-actions { display: flex; gap: 0.5rem; }
    .extension-groups { border: 1px solid var(--border); border-radius: var(--radius-lg); }
    .extension-group { border-bottom: 1px solid var(--border); &:last-child { border-bottom: none; } }
    .group-header { display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; cursor: pointer; }
    .group-info { display: flex; align-items: center; gap: 0.5rem; }
    .group-content { display: none; padding: 0.5rem; gap: 0.5rem; flex-wrap: wrap; &.expanded { display: flex; } }
    .subdirectories-check { margin-top: 1rem; }
    .analysis-field { width: 100%; margin-top: 1rem; }
    .question-block { display: flex; align-items: center; gap: 1rem; }
    .tags-field { margin-top: 2rem; }
    .analyze-btn { margin-top: 2rem; width: 100%; padding: 1.5rem; font-size: 1.2rem; }
  `]
})
export class DeepResearchComponent {
  rootPath: string = "";
  isRecursive: boolean = false;
  filesExts: string[] = [];

  // Analysis Schema
  summaryPrompt: string = "Résume le document suivant :";
  complementaryQuestions: { question: string, isYesNo: boolean }[] = [];
  tags: string = "";
  analysisResult: any = null;


  extensionGroups: ExtensionGroup[] = [
    {
      name: 'Documents',
      icon: 'description',
      extensions: ['.pdf', '.doc', '.docx', '.txt', '.md'],
      selected: 0,
      total: 5,
      expanded: false
    },
    {
      name: 'Images',
      icon: 'image',
      extensions: ['.jpg', '.jpeg', '.png', '.gif', '.svg'],
      selected: 0,
      total: 5,
      expanded: false
    },
    {
      name: 'Audio',
      icon: 'audiotrack',
      extensions: ['.mp3', '.wav', '.ogg', '.m4a', '.flac'],
      selected: 0,
      total: 5,
      expanded: false
    },
    {
      name: 'Video',
      icon: 'movie',
      extensions: ['.mp4', '.avi', '.mkv', '.mov', '.wmv'],
      selected: 0,
      total: 5,
      expanded: false
    },
    {
      name: 'Archives',
      icon: 'folder_zip',
      extensions: ['.zip', '.rar', '.7z', '.tar', '.gz'],
      selected: 0,
      total: 5,
      expanded: false
    },
    {
      name: 'Code',
      icon: 'code',
      extensions: ['.js', '.ts', '.py', '.java', '.html', '.css', '.json', '.php', '.cpp'],
      selected: 0,
      total: 9,
      expanded: false
    },
    {
      name: 'Data',
      icon: 'storage',
      extensions: ['.csv', '.xlsx', '.xml', '.sql', '.db', '.json'],
      selected: 0,
      total: 6,
      expanded: false
    }
  ];

  constructor(private dataService: DataService) {
    this.updateSelectedCounts();
  }

  startAnalysis(): void {
    const payload = {
      root_path: this.rootPath,
      recursive: this.isRecursive,
      required_exts: this.filesExts,
      summary_prompt: this.summaryPrompt,
      complementary_questions: this.complementaryQuestions,
      tags: this.tags
    };
    this.dataService.startDeepAnalysis(payload).subscribe(result => {
      this.analysisResult = result;
    });
  }

  onPathChange(value: string) {
    this.rootPath = value.replaceAll("\\\\", "/").replaceAll("\\", "/")
  }

  toggleGroup(group: ExtensionGroup) {
    group.expanded = !group.expanded;
  }

  updateSelectedCounts() {
    this.extensionGroups.forEach(group => {
      group.selected = group.extensions.filter(ext => this.filesExts.includes(ext)).length;
    });
  }

  selectAll() {
    this.filesExts = this.extensionGroups.flatMap(group => group.extensions);
    this.updateSelectedCounts();
  }

  clearAll() {
    this.filesExts = [];
    this.updateSelectedCounts();
  }

  isExtensionSelected(ext: string): boolean {
    return this.filesExts.includes(ext);
  }

  toggleExtension(ext: string, group: ExtensionGroup) {
    const index = this.filesExts.indexOf(ext);
    if (index === -1) {
      this.filesExts.push(ext);
    } else {
      this.filesExts.splice(index, 1);
    }
    group.selected = group.extensions.filter(ext => this.filesExts.includes(ext)).length;
  }

  addQuestion(): void {
    this.complementaryQuestions.push({ question: '', isYesNo: false });
  }
}
