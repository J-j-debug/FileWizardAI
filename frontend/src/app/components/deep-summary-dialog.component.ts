import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { DataService } from '../data.service';

@Component({
  selector: 'app-deep-summary-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatProgressSpinnerModule, MatTabsModule],
  template: `
    <h2 mat-dialog-title>Deep Summary Result</h2>
    <div mat-dialog-content>
      <div *ngIf="loading" class="loading-container">
        <mat-spinner diameter="40"></mat-spinner>
        <p>Generating summary using Map-Reduce (this may take a minute)...</p>
      </div>
      
      <div *ngIf="!loading && summary">
        <mat-tab-group>
            <mat-tab label="Final Summary">
                <div class="summary-content markdown-body">
                    {{ summary.deep_summary }}
                </div>
            </mat-tab>
            <mat-tab label="Chapter Summaries" *ngIf="summary.intermediate_summaries?.length">
                <div class="intermediate-list">
                    <div *ngFor="let item of summary.intermediate_summaries; let i = index" class="chunk-item">
                        <strong>Part {{i + 1}}:</strong>
                        <p>{{ item }}</p>
                        <hr>
                    </div>
                </div>
            </mat-tab>
            <mat-tab label="Original Text (Chunks)" *ngIf="summary.original_chunks?.length">
                <div class="intermediate-list">
                    <div *ngFor="let chunk of summary.original_chunks; let i = index" class="chunk-item">
                        <strong>Part {{i + 1}} (Original):</strong>
                        <pre class="original-text">{{ chunk }}</pre>
                        <hr>
                    </div>
                </div>
            </mat-tab>
        </mat-tab-group>
        
        <p *ngIf="summary.cached" class="cache-badge">Fetched from Cache</p>
      </div>

       <div *ngIf="!loading && !summary && error" class="error-msg">
            {{error}}
       </div>
    </div>
    <div mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Close</button>
    </div>
  `,
  styles: [`
    .loading-container { display: flex; flex-direction: column; align-items: center; padding: 2rem; }
    .summary-content { white-space: pre-wrap; padding: 1rem; line-height: 1.6; }
    .cache-badge { font-size: 0.8rem; color: #666; margin-top: 1rem; font-style: italic; }
    .intermediate-list { padding: 1rem; max-height: 400px; overflow-y: auto; }
    .chunk-item { margin-bottom: 1rem; }
    .error-msg { color: red; padding: 1rem; }
    .original-text {
        white-space: pre-wrap;
        background: #f5f5f5;
        padding: 10px;
        border-radius: 4px;
        font-size: 0.9em;
        max-height: 500px;
        overflow-y: auto;
        border: 1px solid #ddd;
    }
  `]
})
export class DeepSummaryDialogComponent implements OnInit {
  loading = true;
  summary: any = null; // Object { deep_summary: string, intermediate_summaries: string[], cached: boolean }
  error: string | null = null;

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: { filePath: string },
    private dataService: DataService
  ) { }

  ngOnInit() {
    this.dataService.generateDeepSummary(this.data.filePath).subscribe({
      next: (res: any) => {
        this.summary = res;
        this.loading = false;
      },
      error: (err: any) => {
        this.error = "Failed to generate summary.";
        this.loading = false;
      }
    });
  }
}
