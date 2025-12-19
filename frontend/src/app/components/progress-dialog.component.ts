import { Component, Inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { DataService } from '../data.service';
import { interval, Subscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

@Component({
    selector: 'app-progress-dialog',
    standalone: true,
    imports: [
        CommonModule,
        MatDialogModule,
        MatProgressBarModule,
        MatButtonModule,
        MatExpansionModule,
        MatIconModule
    ],
    template: `
    <h2 mat-dialog-title>Execution In Progress</h2>
    <mat-dialog-content>
      <p class="status-message">{{ status }}</p>
      
      <mat-progress-bar mode="determinate" [value]="percent"></mat-progress-bar>
      <div class="percent-label">{{ percent }}%</div>

      <mat-expansion-panel class="logs-panel" [expanded]="true">
        <mat-expansion-panel-header>
          <mat-panel-title>
            Logs ({{ logs.length }})
          </mat-panel-title>
        </mat-expansion-panel-header>
        <div class="logs-container" #logContainer>
          <div *ngFor="let log of logs" class="log-entry">
            <span class="log-time">{{ getTimestamp() }}</span> {{ log }}
          </div>
        </div>
      </mat-expansion-panel>

    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <!-- Close button is disabled until complete, unless we want to allow backgrounding -->
      <button mat-button (click)="close()" [disabled]="!isComplete">Fermer</button>
    </mat-dialog-actions>
  `,
    styles: [`
    .status-message {
      font-size: 1.1rem;
      margin-bottom: 1rem;
    }
    .percent-label {
        text-align: right;
        font-size: 0.8rem;
        color: #888;
        margin-top: 5px;
        margin-bottom: 1rem;
    }
    .logs-panel {
        margin-top: 1rem;
        background: #f5f5f5;
    }
    .logs-container {
        max-height: 200px;
        overflow-y: auto;
        font-family: monospace;
        font-size: 0.85rem;
        padding: 0.5rem;
    }
    .log-entry {
        border-bottom: 1px solid #eee;
        padding: 2px 0;
    }
    .log-time {
        color: #888;
        font-size: 0.7rem;
        margin-right: 5px;
    }
  `]
})
export class ProgressDialogComponent implements OnInit, OnDestroy {
    status: string = "Initializing...";
    percent: number = 0;
    logs: string[] = [];
    isComplete: boolean = false;
    private pollSubscription!: Subscription;

    constructor(
        public dialogRef: MatDialogRef<ProgressDialogComponent>,
        @Inject(MAT_DIALOG_DATA) public data: any,
        private dataService: DataService
    ) { }

    ngOnInit() {
        this.startPolling();
    }

    startPolling() {
        // Poll every 500ms
        this.pollSubscription = interval(500).pipe(
            switchMap(() => this.dataService.getProgress())
        ).subscribe(
            (data) => {
                this.status = data.status;
                this.percent = data.percent;
                this.logs = data.logs || [];

                if (this.percent >= 100) {
                    this.isComplete = true;
                    this.status = "Completed!";
                }
            },
            (error) => {
                console.error("Polling error", error);
                this.status = "Error retrieving progress";
                this.logs.push("Connection error...");
            }
        );
    }

    getTimestamp() {
        return new Date().toLocaleTimeString();
    }

    close() {
        this.dialogRef.close();
    }

    ngOnDestroy() {
        if (this.pollSubscription) {
            this.pollSubscription.unsubscribe();
        }
    }
}
