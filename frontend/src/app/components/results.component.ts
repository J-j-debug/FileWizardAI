import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-results',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule
  ],
  template: `
    <div class="results-container">
      <h3>Résultats de l'Analyse</h3>

      <div class="filters-container">
        <!-- Tag Filter -->
        <mat-form-field appearance="outline">
          <mat-label>Filtrer par Tags</mat-label>
          <mat-select [(ngModel)]="selectedTags" (selectionChange)="applyFilters()" multiple>
            <mat-option *ngFor="let tag of availableTags" [value]="tag">{{ tag }}</mat-option>
          </mat-select>
        </mat-form-field>

        <!-- Question Filter -->
        <mat-form-field appearance="outline">
          <mat-label>Question</mat-label>
          <mat-select [(ngModel)]="selectedQuestion" (selectionChange)="applyFilters()">
            <mat-option *ngFor="let question of availableQuestions" [value]="question">{{ question }}</mat-option>
          </mat-select>
        </mat-form-field>

        <!-- Answer Filter -->
        <mat-form-field appearance="outline">
          <mat-label>Réponse</mat-label>
          <mat-select [(ngModel)]="selectedAnswer" (selectionChange)="applyFilters()">
            <mat-option value="Oui">Oui</mat-option>
            <mat-option value="Non">Non</mat-option>
          </mat-select>
        </mat-form-field>

        <button mat-stroked-button color="warn" (click)="resetFilters()">
          <mat-icon>clear</mat-icon>
          Réinitialiser
        </button>
      </div>

      <table *ngIf="filteredResults && filteredResults.length > 0">
        <thead>
          <tr>
            <th>Fichier</th>
            <th>Résumé</th>
            <th *ngFor="let question of availableQuestions">{{ question }}</th>
            <th>Tags</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let result of filteredResults">
            <td>{{ result.file_path }}</td>
            <td>{{ result.analysis.summary }}</td>
            <td *ngFor="let question of availableQuestions">
              {{ result.analysis.questions[question] }}
            </td>
            <td>
                <span *ngFor="let tag of getObjectKeys(result.analysis.tags)">
                    {{ tag }}: {{ result.analysis.tags[tag] }} <br>
                </span>
            </td>
          </tr>
        </tbody>
      </table>
      <p *ngIf="!filteredResults || filteredResults.length === 0">
        Aucun résultat à afficher (ou correspondant à vos filtres).
      </p>
    </div>
  `,
  styles: [`
    .results-container { margin-top: 2rem; }
    .filters-container {
      display: flex;
      gap: 1rem;
      align-items: center;
      margin-bottom: 1.5rem;
      padding: 1rem;
      background-color: var(--surface-variant);
      border-radius: var(--radius-lg);
    }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid var(--border); padding: 8px; text-align: left; }
    th { background-color: var(--surface-variant); }
  `]
})
export class ResultsComponent implements OnChanges {
  @Input() results: any[] = [];

  filteredResults: any[] = [];
  availableTags: string[] = [];
  availableQuestions: string[] = [];

  // Filter state
  selectedTags: string[] = [];
  selectedQuestion: string | null = null;
  selectedAnswer: string | null = null;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['results']) {
      this.resetFilters();
      this.extractFilters();
    }
  }

  applyFilters(): void {
    let results = [...this.results];

    // Filter by tags
    if (this.selectedTags.length > 0) {
      results = results.filter(result => {
        if (!result.analysis.tags || typeof result.analysis.tags !== 'object') {
          return false;
        }
        return this.selectedTags.every(tag => {
          const tagValue = result.analysis.tags[tag];
          // Normalize tag value for robust 'oui' check
          const normalizedTagValue = String(tagValue).trim().toLowerCase().replace(/[\.\s]/g, '');
          return ['oui', 'yes', 'true', 'vrai'].includes(normalizedTagValue);
        });
      });
    }

    // Filter by question and answer
    if (this.selectedQuestion && this.selectedAnswer) {
        results = results.filter(result => {
            const answer = result.analysis.questions[this.selectedQuestion!];
            if (answer === undefined || answer === null) {
                return false;
            }
            // Robust normalization for comparison
            const normalizedAnswer = String(answer).trim().toLowerCase().replace(/[\.\s]/g, '');
            const normalizedFilter = this.selectedAnswer!.trim().toLowerCase();
            if (normalizedFilter === 'oui') {
                return ['oui', 'yes', 'true', 'vrai'].includes(normalizedAnswer);
            } else if (normalizedFilter === 'non') {
                return ['non', 'no', 'false', 'faux'].includes(normalizedAnswer);
            }
            return false;
        });
    }

    this.filteredResults = results;
  }

  resetFilters(): void {
    this.selectedTags = [];
    this.selectedQuestion = null;
    this.selectedAnswer = null;
    this.filteredResults = [...this.results];
  }

  extractFilters(): void {
    const tags = new Set<string>();
    const questions = new Set<string>();

    this.results.forEach(result => {
      // Extract tags
      if (result.analysis.tags && typeof result.analysis.tags === 'object') {
        Object.keys(result.analysis.tags).forEach(tag => tags.add(tag));
      }

      // Extract questions
      if (result.analysis.questions) {
        Object.keys(result.analysis.questions).forEach(q => questions.add(q));
      }
    });

    this.availableTags = Array.from(tags);
    this.availableQuestions = Array.from(questions);
  }

  getObjectKeys(obj: any): string[] {
    if (!obj || typeof obj !== 'object') {
      return [];
    }
    return Object.keys(obj);
  }
}
