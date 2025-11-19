import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-results',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="results-container">
      <h3>Résultats de l'Analyse</h3>
      <table *ngIf="results && results.length > 0">
        <thead>
          <tr>
            <th>Fichier</th>
            <th>Résumé</th>
            <th *ngFor="let question of getQuestionKeys(results[0])">{{ question }}</th>
            <th>Tags</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let result of results">
            <td>{{ result.file_path }}</td>
            <td>{{ result.analysis.summary }}</td>
            <td *ngFor="let question of getQuestionKeys(result)">
              {{ result.analysis.questions[question] }}
            </td>
            <td>{{ result.analysis.tags }}</td>
          </tr>
        </tbody>
      </table>
      <p *ngIf="!results || results.length === 0">
        Aucun résultat à afficher.
      </p>
    </div>
  `,
  styles: [`
    .results-container { margin-top: 2rem; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid var(--border); padding: 8px; text-align: left; }
    th { background-color: var(--surface-variant); }
  `]
})
export class ResultsComponent {
  @Input() results: any[] = [];

  getQuestionKeys(result: any): string[] {
    if (!result || !result.analysis || !result.analysis.questions) {
      return [];
    }
    return Object.keys(result.analysis.questions);
  }
}
